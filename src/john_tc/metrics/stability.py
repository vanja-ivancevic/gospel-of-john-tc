"""Textual-stability map — the complement of the instability analysis.

Where is the text of John FIRM (the whole tradition agrees) vs fluid? Reported as:
  consensus      = support of the majority reading / extant witnesses, per variation unit
  verse stability = mean consensus over a verse's units
  anchors        = units the tradition agrees on almost unanimously (consensus >= 0.99)
  family homogeneity = how internally consistent each family is (1 - mean pairwise distance)
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from john_tc.config import load_config

_CONSENSUS_SQL = """
WITH nonlac AS (
  SELECT r.app_id, r.reading_id, a.base_ga
  FROM readings r
  JOIN attestation a ON a.app_id=r.app_id AND a.reading_id=r.reading_id
  JOIN units u ON u.app_id=r.app_id
  WHERE u.app_type='main' AND r.reading_type IS DISTINCT FROM 'lac'
  GROUP BY 1,2,3),
ext AS (SELECT app_id, count(DISTINCT base_ga) AS extant FROM nonlac GROUP BY 1),
rdg AS (SELECT app_id, reading_id, count(DISTINCT base_ga) AS n FROM nonlac GROUP BY 1,2),
mx  AS (SELECT app_id, max(n) AS nmax FROM rdg GROUP BY 1)
SELECT u.app_id, u.chapter, u.verse, u.verse_id,
       mx.nmax::DOUBLE / ext.extant AS consensus, ext.extant
FROM units u JOIN mx ON mx.app_id=u.app_id JOIN ext ON ext.app_id=u.app_id
WHERE u.app_type='main'
"""


def _con(db_path=None):
    return duckdb.connect(str(db_path or load_config().path("collation_db")), read_only=True)


def unit_consensus(db_path: Path | None = None) -> pd.DataFrame:
    con = _con(db_path)
    df = con.execute(_CONSENSUS_SQL).df()
    con.close()
    df["is_anchor"] = df["consensus"] >= 0.99
    return df


def verse_stability(db_path: Path | None = None) -> pd.DataFrame:
    u = unit_consensus(db_path)
    return (u.groupby(["chapter", "verse", "verse_id"], as_index=False)
              .agg(stability=("consensus", "mean"), n_units=("app_id", "count"),
                   anchor_frac=("is_anchor", "mean")))


def family_homogeneity(db_path: Path | None = None) -> dict:
    """Internal consistency of each family = 1 - mean pairwise coherence distance."""
    from john_tc.metrics.families import assign_families
    from john_tc.metrics.genealogy import coherence_distance, informative_mask, reading_matrix

    wits, codes = reading_matrix(db_path)
    dist = coherence_distance(wits, codes[informative_mask(codes)])
    fam = dict(zip(*[assign_families(db_path)[c] for c in ("base_ga", "family")]))
    idx = {w: i for i, w in enumerate(wits)}
    out = {}
    for f in ("f1", "f13", "Byz", "Alexandrian"):
        members = [w for w in wits if fam.get(w) == f]
        ds = [dist[idx[a]][idx[b]] for i, a in enumerate(members) for b in members[i + 1:]]
        if ds:
            out[f] = round(1 - float(np.mean(ds)), 3)
    return out


def summarize(db_path: Path | None = None) -> dict:
    u = unit_consensus(db_path)
    v = verse_stability(db_path).sort_values("stability", ascending=False)
    chap = (v.groupby("chapter", as_index=False)
              .agg(stability=("stability", "mean"), anchor_frac=("anchor_frac", "mean")))
    return {
        "n_units": len(u),
        "anchor_units": int(u.is_anchor.sum()),
        "anchor_frac": round(float(u.is_anchor.mean()), 3),
        "mean_consensus": round(float(u.consensus.mean()), 3),
        "most_stable_verses": v.head(8)[["verse_id", "stability"]].to_records(index=False).tolist(),
        "most_fluid_verses": v.tail(8)[["verse_id", "stability"]].to_records(index=False).tolist(),
        "most_stable_chapters": chap.sort_values("stability", ascending=False)
            .head(5).chapter.tolist(),
        "least_stable_chapters": chap.sort_values("stability").head(5).chapter.tolist(),
        "family_homogeneity": family_homogeneity(db_path),
    }


def build(db_path: Path | None = None) -> dict:
    cfg = load_config()
    db_path = db_path or cfg.path("collation_db")
    u = unit_consensus(db_path)  # noqa: F841 — used by name in DuckDB SQL below
    v = verse_stability(db_path)  # noqa: F841 — used by name in DuckDB SQL below
    con = duckdb.connect(str(db_path))
    con.execute("CREATE OR REPLACE TABLE metrics_unit_consensus AS SELECT * FROM u")
    con.execute("CREATE OR REPLACE TABLE metrics_verse_stability AS SELECT * FROM v")
    con.close()
    return summarize(db_path)


def write_report(path: Path | None = None, db_path: Path | None = None) -> Path:
    cfg = load_config()
    path = path or cfg.path("reports") / "analysis" / "STABILITY.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    s = summarize(db_path)
    L = ["# Textual-stability map of John", "",
         f"- Mean consensus (majority-reading support / extant witnesses): **{s['mean_consensus']}**",
         f"- Anchor units (consensus ≥ 0.99, near-unanimous): **{s['anchor_units']} / {s['n_units']}** "
         f"({s['anchor_frac']:.0%})",
         f"- Most stable chapters: {s['most_stable_chapters']}",
         f"- Least stable chapters: {s['least_stable_chapters']}", "",
         "## Most stable verses (whole tradition agrees)"]
    for vid, st in s["most_stable_verses"]:
        L.append(f"- {vid}: {st:.3f}")
    L.append("\n## Most fluid verses (tradition most divided)")
    for vid, st in s["most_fluid_verses"]:
        L.append(f"- {vid}: {st:.3f}")
    L += ["", "## Family internal homogeneity (1 − mean within-family distance)"]
    for f, h in s["family_homogeneity"].items():
        L.append(f"- {f}: {h}")
    path.write_text("\n".join(L), encoding="utf-8")
    return path


def main() -> None:
    s = build()
    print(f"mean consensus {s['mean_consensus']}, anchors {s['anchor_units']}/{s['n_units']} "
          f"({s['anchor_frac']:.0%})")
    print("most stable chapters:", s["most_stable_chapters"])
    print("least stable chapters:", s["least_stable_chapters"])
    print("family homogeneity:", s["family_homogeneity"])
    print("most stable verses:", [v for v, _ in s["most_stable_verses"]][:5])
    print("most fluid verses:", [v for v, _ in s["most_fluid_verses"]][:5])
    print("report:", write_report())


if __name__ == "__main__":
    main()
