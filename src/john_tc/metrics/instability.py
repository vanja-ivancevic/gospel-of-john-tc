"""Witness-normalized transmission-instability metrics (RQ1) and coverage (RQ3).

Every metric is normalized by the witnesses *actually attesting* each unit (extant =
not lacunose), so it cannot be inflated by a single heavily-corrected codex — the exact
failure mode of the discarded variant database.

Definitions (per substantive variation unit, app_type='main'):
  extant    = distinct base manuscripts citing a non-lacunose reading
  lemma     = distinct base manuscripts supporting the NA28 base reading
  diverge   = distinct base manuscripts supporting a substantive non-lemma reading
              (reading_type NULL or 'om'; orthographic 'subreading' excluded)
  instability = |diverge| / |extant|        (proportion of witnesses departing from NA28)

Coverage (per verse): how many base manuscripts attest (are extant for) the verse.
A localized trough = an editorially omitted unit (e.g. the Pericope Adulterae).
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from john_tc.config import load_config

# One reading per (unit, witness): firsthand hand wins, so a codex's own corrector cannot make
# it count as both agreeing and diverging (the intra-MS artifact the rebuild exists to remove).
# 'basetext' (the editorial NA28 base) is not a manuscript -> excluded. Orthographic 'subreading'
# is folded into agreement, matching the stability metric (one shared substantive-disagreement rule).
_UNIT_SQL = """
WITH att AS (
    SELECT r.app_id, r.reading_id, r.is_lemma, r.reading_type, a.base_ga, a.hand
    FROM readings r
    JOIN attestation a ON a.app_id = r.app_id AND a.reading_id = r.reading_id
    JOIN units u ON u.app_id = r.app_id
    WHERE u.app_type = 'main' AND r.reading_type IS DISTINCT FROM 'lac'
          AND a.base_ga <> 'basetext'
),
pick AS (
    SELECT app_id, base_ga, is_lemma, reading_type,
      row_number() OVER (PARTITION BY app_id, base_ga
        ORDER BY CASE WHEN hand = 'firsthand' THEN 0 ELSE 1 END,
                 CASE WHEN is_lemma OR reading_type = 'subreading' THEN 0 ELSE 1 END,
                 reading_id) AS rn
    FROM att
),
one AS (SELECT app_id, base_ga, is_lemma, reading_type FROM pick WHERE rn = 1),
ext AS (SELECT app_id, count(*) AS n_extant FROM one GROUP BY 1),
lem AS (SELECT app_id, count(*) AS n_lemma FROM one
        WHERE is_lemma OR reading_type = 'subreading' GROUP BY 1),
div AS (SELECT app_id, count(*) AS n_diverge FROM one
        WHERE NOT is_lemma AND (reading_type IS NULL OR reading_type = 'om') GROUP BY 1)
SELECT u.app_id, u.verse_id, u.chapter, u.verse,
       coalesce(ext.n_extant, 0) AS n_extant,
       coalesce(lem.n_lemma, 0)  AS n_lemma,
       coalesce(div.n_diverge, 0) AS n_diverge,
       (SELECT count(*) FROM readings r WHERE r.app_id = u.app_id
            AND (r.reading_type IS NULL OR r.reading_type = 'om')) AS n_subst_readings
FROM units u
LEFT JOIN ext ON ext.app_id = u.app_id
LEFT JOIN lem ON lem.app_id = u.app_id
LEFT JOIN div ON div.app_id = u.app_id
WHERE u.app_type = 'main'
"""


def _con(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    cfg = load_config()
    return duckdb.connect(str(db_path or cfg.path("collation_db")))


def unit_instability(db_path: Path | None = None) -> pd.DataFrame:
    con = _con(db_path)
    df = con.execute(_UNIT_SQL).df()
    con.close()
    df["instability"] = df["n_diverge"] / df["n_extant"].where(df["n_extant"] > 0)
    return df


def verse_metrics(db_path: Path | None = None) -> pd.DataFrame:
    """Per-verse: mean instability (witness-normalized) + coverage (extant base MS)."""
    u = unit_instability(db_path)
    g = u.groupby(["chapter", "verse", "verse_id"], as_index=False).agg(
        n_units=("app_id", "count"),
        instability=("instability", "mean"),
        n_diverge_sum=("n_diverge", "sum"),
        n_extant_mean=("n_extant", "mean"),
    )
    # Coverage = distinct real manuscripts extant in the verse (basetext is the editorial NA28
    # base, not a witness -> excluded). Genealogical-depth confidence (effective independent
    # witnesses / family breadth / early support) is derived later in the dashboard export, once
    # family + date metadata exist; raw coverage alone overstates evidence (witnesses are weighed,
    # not counted).
    con = _con(db_path)
    cov = con.execute(
        """
        WITH att AS (
            SELECT u.verse_id, a.base_ga
            FROM units u
            JOIN readings r ON r.app_id = u.app_id
            JOIN attestation a ON a.app_id = r.app_id AND a.reading_id = r.reading_id
            WHERE u.app_type = 'main' AND r.reading_type IS DISTINCT FROM 'lac'
                  AND a.base_ga <> 'basetext'
            GROUP BY 1, 2)
        SELECT verse_id, count(*) AS extant_base_ms FROM att GROUP BY 1
        """
    ).df()
    con.close()
    out = g.merge(cov, on="verse_id", how="left").sort_values(["chapter", "verse"])
    return out.reset_index(drop=True)


def chapter_metrics(db_path: Path | None = None) -> pd.DataFrame:
    v = verse_metrics(db_path)
    return v.groupby("chapter", as_index=False).agg(
        n_verses=("verse_id", "count"),
        n_units=("n_units", "sum"),
        instability=("instability", "mean"),
        coverage_mean=("extant_base_ms", "mean"),
    )


def build_metric_tables(db_path: Path | None = None) -> dict[str, int]:
    """Persist unit/verse/chapter metrics back into the DuckDB store."""
    cfg = load_config()
    db_path = db_path or cfg.path("collation_db")
    u, v, c = unit_instability(db_path), verse_metrics(db_path), chapter_metrics(db_path)
    con = duckdb.connect(str(db_path))
    for name, df in [("metrics_unit", u), ("metrics_verse", v), ("metrics_chapter", c)]:
        con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM df")
    con.close()
    return {"units": len(u), "verses": len(v), "chapters": len(c)}


def main() -> None:
    n = build_metric_tables()
    c = chapter_metrics()
    print("Metric tables built:", n)
    print(c.to_string(index=False))


if __name__ == "__main__":
    main()
