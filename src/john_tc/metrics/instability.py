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

# A base_ga is "extant" at a unit if it appears in any non-lacuna reading.
# It "diverges" if it supports a substantive (non-lemma, non-orthographic) reading.
_UNIT_SQL = """
WITH att AS (
    SELECT r.app_id, r.reading_id, r.is_lemma, r.reading_type, a.base_ga
    FROM readings r
    JOIN attestation a ON a.app_id = r.app_id AND a.reading_id = r.reading_id
    JOIN units u ON u.app_id = r.app_id
    WHERE u.app_type = 'main'
),
extant AS (
    SELECT app_id, base_ga FROM att
    WHERE reading_type IS DISTINCT FROM 'lac'
    GROUP BY 1, 2
),
lemma AS (
    SELECT app_id, base_ga FROM att WHERE is_lemma GROUP BY 1, 2
),
diverge AS (
    SELECT app_id, base_ga FROM att
    WHERE NOT is_lemma AND (reading_type IS NULL OR reading_type = 'om')
    GROUP BY 1, 2
)
SELECT u.app_id, u.verse_id, u.chapter, u.verse,
       (SELECT count(*) FROM extant e WHERE e.app_id = u.app_id)  AS n_extant,
       (SELECT count(*) FROM lemma l WHERE l.app_id = u.app_id)   AS n_lemma,
       (SELECT count(*) FROM diverge d WHERE d.app_id = u.app_id) AS n_diverge,
       (SELECT count(*) FROM readings r WHERE r.app_id = u.app_id
            AND (r.reading_type IS NULL OR r.reading_type = 'om')) AS n_subst_readings
FROM units u
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
    # Coverage: distinct base MS extant anywhere in the verse (presence/absence signal).
    con = _con(db_path)
    cov = con.execute(
        """
        WITH att AS (
            SELECT u.verse_id, a.base_ga
            FROM units u
            JOIN readings r ON r.app_id = u.app_id
            JOIN attestation a ON a.app_id = r.app_id AND a.reading_id = r.reading_id
            WHERE u.app_type = 'main' AND r.reading_type IS DISTINCT FROM 'lac'
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
