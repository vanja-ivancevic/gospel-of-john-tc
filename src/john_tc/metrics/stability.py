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

# Flat consensus ("raw agreement", witnesses counted): one reading per (unit, witness) with
# firsthand priority (no corrector double-count), basetext excluded, orthographic subreadings folded
# into agreement ('base'). Reports a tie flag when two readings share the plurality.
_CONSENSUS_SQL = """
WITH att AS (
  SELECT r.app_id, r.reading_id, r.is_lemma, r.reading_type, a.base_ga, a.hand
  FROM readings r
  JOIN attestation a ON a.app_id=r.app_id AND a.reading_id=r.reading_id
  JOIN units u ON u.app_id=r.app_id
  WHERE u.app_type='main' AND r.reading_type IS DISTINCT FROM 'lac' AND a.base_ga <> 'basetext'),
pick AS (
  SELECT app_id, base_ga,
    CASE WHEN is_lemma OR reading_type='subreading' THEN 'base'
         ELSE CAST(reading_id AS VARCHAR) END AS grp,
    row_number() OVER (PARTITION BY app_id, base_ga
      ORDER BY CASE WHEN hand='firsthand' THEN 0 ELSE 1 END,
               CASE WHEN is_lemma OR reading_type='subreading' THEN 0 ELSE 1 END,
               reading_id) AS rn
  FROM att),
one AS (SELECT app_id, base_ga, grp FROM pick WHERE rn=1),
ext AS (SELECT app_id, count(*) AS extant FROM one GROUP BY 1),
rdg AS (SELECT app_id, grp, count(*) AS n FROM one GROUP BY 1,2),
mx  AS (SELECT app_id, max(n) AS nmax FROM rdg GROUP BY 1),
tie AS (SELECT m.app_id, m.nmax, count(*) AS n_at_max
        FROM mx m JOIN rdg r ON r.app_id=m.app_id AND r.n=m.nmax GROUP BY 1,2)
SELECT u.app_id, u.chapter, u.verse, u.verse_id,
       tie.nmax::DOUBLE / NULLIF(ext.extant,0) AS consensus,
       ext.extant, (tie.n_at_max > 1) AS tied
FROM units u JOIN tie ON tie.app_id=u.app_id JOIN ext ON ext.app_id=u.app_id
WHERE u.app_type='main'
"""

# Family-vote consensus ("weighed, not counted"): each family casts its plurality reading; consensus
# = share of families on the modal family-reading. Neutralises Byzantine over-representation — the
# critical-text view. (Note: Byzantine-priority scholars dispute treating Byz as one voice, so the
# flat metric above is kept and shown alongside.)
_FAMILY_CONSENSUS_SQL = """
-- Family vote: only witnesses carrying a family label vote, so the metric matches
-- weighted_instability's population. Metadata-less sigla (lectionaries, versions without an
-- assigned family) are excluded rather than folded into a heterogeneous 'other' that would vote
-- as if it were a single coherent family.
WITH att AS (
  SELECT r.app_id, r.reading_id, r.is_lemma, r.reading_type, a.base_ga, a.hand, m.family
  FROM readings r
  JOIN attestation a ON a.app_id=r.app_id AND a.reading_id=r.reading_id
  JOIN units u ON u.app_id=r.app_id
  JOIN witness_metadata m ON m.base_ga=a.base_ga
  WHERE u.app_type='main' AND r.reading_type IS DISTINCT FROM 'lac'
        AND a.base_ga <> 'basetext' AND m.family IS NOT NULL),
pick AS (
  SELECT app_id, family,
    CASE WHEN is_lemma OR reading_type='subreading' THEN 'base'
         ELSE CAST(reading_id AS VARCHAR) END AS grp,
    row_number() OVER (PARTITION BY app_id, base_ga
      ORDER BY CASE WHEN hand='firsthand' THEN 0 ELSE 1 END,
               CASE WHEN is_lemma OR reading_type='subreading' THEN 0 ELSE 1 END,
               reading_id) AS rn
  FROM att),
one AS (SELECT app_id, family, grp FROM pick WHERE rn=1),
fam_rd AS (SELECT app_id, family, grp, count(*) AS n FROM one GROUP BY 1,2,3),
fam_vote AS (
  SELECT app_id, family, grp AS vote FROM (
    SELECT app_id, family, grp,
           row_number() OVER (PARTITION BY app_id, family ORDER BY n DESC, grp) AS rk
    FROM fam_rd) WHERE rk=1),
nf AS (SELECT app_id, count(*) AS n_fam FROM fam_vote GROUP BY 1),
vd AS (SELECT app_id, vote, count(*) AS n FROM fam_vote GROUP BY 1,2),
vmax AS (SELECT app_id, max(n) AS vmax FROM vd GROUP BY 1)
-- family_consensus is only defined when >=2 families are extant; a unit carried by a single
-- family has no cross-family agreement to measure and is left NULL (not scored as 1.0), so it
-- cannot inflate the "all families agree" count or the verse family-stability mean.
SELECT u.app_id, u.verse_id, nf.n_fam,
       CASE WHEN nf.n_fam >= 2 THEN vmax.vmax::DOUBLE / nf.n_fam END AS family_consensus
FROM units u JOIN vmax ON vmax.app_id=u.app_id JOIN nf ON nf.app_id=u.app_id
WHERE u.app_type='main'
"""


def _con(db_path=None):
    return duckdb.connect(str(db_path or load_config().path("collation_db")), read_only=True)


def unit_consensus(db_path: Path | None = None) -> pd.DataFrame:
    con = _con(db_path)
    df = con.execute(_CONSENSUS_SQL).df()
    fam = con.execute(_FAMILY_CONSENSUS_SQL).df()
    con.close()
    df = df.merge(fam[["app_id", "family_consensus", "n_fam"]], on="app_id", how="left")
    df["is_anchor"] = df["consensus"] >= 0.99            # flat near-unanimity
    df["is_family_anchor"] = df["family_consensus"] >= 0.99  # all families agree
    return df


def verse_stability(db_path: Path | None = None) -> pd.DataFrame:
    u = unit_consensus(db_path)
    return (u.groupby(["chapter", "verse", "verse_id"], as_index=False)
              .agg(stability=("consensus", "mean"),
                   family_stability=("family_consensus", "mean"),
                   n_units=("app_id", "count"),
                   anchor_frac=("is_anchor", "mean"),
                   tied_units=("tied", "sum")))


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
    # Headline ranking uses the family-vote ("weighed") metric; flat ("counted") kept alongside.
    # Verses with no multi-family unit have an undefined family-vote and are dropped from the
    # ranking (they cannot be "most fluid"/"most stable" with nothing to compare across families).
    u = unit_consensus(db_path)
    v = (verse_stability(db_path).dropna(subset=["family_stability"])
         .sort_values("family_stability", ascending=False))
    chap = (v.groupby("chapter", as_index=False)
              .agg(family_stability=("family_stability", "mean"),
                   stability=("stability", "mean"), anchor_frac=("anchor_frac", "mean")))
    return {
        "n_units": len(u),
        "anchor_units": int(u.is_anchor.sum()),
        "anchor_frac": round(float(u.is_anchor.mean()), 3),
        "family_anchor_units": int(u.is_family_anchor.sum()),
        "mean_consensus": round(float(u.consensus.mean()), 3),
        "mean_family_consensus": round(float(u.family_consensus.mean()), 3),
        "most_stable_verses":
            v.head(8)[["verse_id", "family_stability"]].to_records(index=False).tolist(),
        "most_fluid_verses":
            v.tail(8)[["verse_id", "family_stability"]].to_records(index=False).tolist(),
        "most_stable_chapters": chap.sort_values("family_stability", ascending=False)
            .head(5).chapter.tolist(),
        "least_stable_chapters": chap.sort_values("family_stability").head(5).chapter.tolist(),
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
         "Two complementary stability metrics (textual criticism's *weighed vs counted* distinction):",
         "",
         f"- **Family-vote stability** (\"weighed\" — each family one plurality vote, Byzantine mass "
         f"counts once): mean **{s['mean_family_consensus']}**. This drives the dashboard headline.",
         f"- **Flat consensus** (\"counted\" — majority-reading support / extant witnesses, every "
         f"witness equal): mean **{s['mean_consensus']}**. Shown alongside as the raw view.",
         f"- Anchor units (flat consensus ≥ 0.99, near-unanimous): **{s['anchor_units']} / "
         f"{s['n_units']}** ({s['anchor_frac']:.0%}); all-families-agree units: "
         f"**{s['family_anchor_units']}**.",
         f"- Most stable chapters (family-vote): {s['most_stable_chapters']}",
         f"- Least stable chapters (family-vote): {s['least_stable_chapters']}", "",
         "## Most stable verses (families agree)"]
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
