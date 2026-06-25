"""Genealogy-aware instability — the analysis the validated families unlock.

Flat instability counts each witness once, so a unit looks "unstable" whenever the ~124
Byzantine copies happen to vary among themselves (late copying noise). Two genealogy-aware
metrics fix this:

  family_instability  = fraction of FAMILIES whose plurality reading departs from the NA28
                        base (one family = one vote; Byzantine counts once, not 124 times)
  between_family_split = do the major families DISAGREE with each other? (a distinct, deeper
                        signal than within-family churn — this is branch-level divergence)

Reported alongside the flat metric so the difference is explicit.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from john_tc.config import load_config

# One firsthand reading per (unit, witness), joined to family + lemma flag, main non-lac units.
_LONG_SQL = """
WITH pick AS (
  SELECT r.app_id, a.base_ga, r.reading_id,
         row_number() OVER (PARTITION BY r.app_id, a.base_ga
            ORDER BY CASE WHEN a.hand='firsthand' THEN 0 ELSE 1 END, r.reading_id) rn
  FROM readings r
  JOIN attestation a ON a.app_id=r.app_id AND a.reading_id=r.reading_id
  JOIN units u ON u.app_id=r.app_id
  WHERE u.app_type='main' AND r.reading_type IS DISTINCT FROM 'lac')
SELECT p.app_id, u.chapter, u.verse_id, p.base_ga, p.reading_id,
       r.is_lemma, m.family
FROM pick p
JOIN units u ON u.app_id=p.app_id
JOIN readings r ON r.app_id=p.app_id AND r.reading_id=p.reading_id
LEFT JOIN witness_metadata m ON m.base_ga=p.base_ga
WHERE p.rn=1 AND m.family IS NOT NULL
"""


def _con(db_path=None):
    return duckdb.connect(str(db_path or load_config().path("collation_db")), read_only=True)


def unit_family_metrics(db_path: Path | None = None) -> pd.DataFrame:
    con = _con(db_path)
    df = con.execute(_LONG_SQL).df()
    con.close()

    # plurality reading per (unit, family); track whether that plurality is the lemma
    grp = (df.groupby(["app_id", "chapter", "verse_id", "family", "reading_id"])
             .agg(n=("base_ga", "count"), is_lemma=("is_lemma", "max")).reset_index())
    grp = grp.sort_values(["app_id", "family", "n"], ascending=[True, True, False])
    fam_plurality = grp.drop_duplicates(["app_id", "family"])  # top reading per family

    def per_unit(g):
        n_fam = len(g)
        n_div = int((~g.is_lemma.astype(bool)).sum())          # families departing from base
        n_distinct = g.reading_id.nunique()                    # distinct family pluralities
        return pd.Series({
            "chapter": g.chapter.iloc[0], "verse_id": g.verse_id.iloc[0],
            "n_families": n_fam,
            "family_instability": n_div / n_fam if n_fam else 0.0,
            "between_family_split": bool(n_distinct > 1),
        })

    out = fam_plurality.groupby("app_id", group_keys=False).apply(per_unit, include_groups=False)
    return out.reset_index()


def chapter_comparison(db_path: Path | None = None) -> pd.DataFrame:
    """Flat instability vs family-vote instability vs between-family split, per chapter."""
    from john_tc.metrics.instability import verse_metrics

    fam = unit_family_metrics(db_path)
    by_chap_fam = fam.groupby("chapter", as_index=False).agg(
        n_units=("app_id", "count"),
        family_instability=("family_instability", "mean"),
        between_family_split=("between_family_split", "mean"),
    )
    flat = verse_metrics(db_path).groupby("chapter", as_index=False).agg(
        flat_instability=("instability", "mean"))
    return flat.merge(by_chap_fam, on="chapter").sort_values("chapter").reset_index(drop=True)


def build(db_path: Path | None = None) -> pd.DataFrame:
    cfg = load_config()
    db_path = db_path or cfg.path("collation_db")
    unit = unit_family_metrics(db_path)  # noqa: F841 — used by name in DuckDB SQL below
    chap = chapter_comparison(db_path)
    con = duckdb.connect(str(db_path))
    con.execute("CREATE OR REPLACE TABLE metrics_unit_family AS SELECT * FROM unit")
    con.execute("CREATE OR REPLACE TABLE metrics_chapter_family AS SELECT * FROM chap")
    con.close()
    return chap


def plot_comparison(db_path: Path | None = None) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cfg = load_config()
    chap = chapter_comparison(db_path)
    path = cfg.path("reports") / "instability" / "chapter_instability_flat_vs_genealogy.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(13, 6))
    x = chap["chapter"]
    ax.plot(x, chap.flat_instability, "o-", label="flat (1 witness = 1 vote)", color="#7f7f7f")
    ax.plot(x, chap.family_instability, "s-", label="family-vote (Byz counts once)", color="#1f77b4")
    ax.plot(x, chap.between_family_split, "^--",
            label="between-family split (branches disagree)", color="#d62728")
    ax.set_xticks(x)
    ax.set_xlabel("John chapter")
    ax.set_ylabel("instability / split fraction")
    ax.set_title("Gospel of John — instability: flat vs genealogy-aware")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def main() -> None:
    chap = build()
    pd.set_option("display.width", 140)
    print(chap.round(3).to_string(index=False))
    print("\nFigure:", plot_comparison())
    # headline: does the genealogy-aware view change the chapter ranking?
    print("\nMost unstable chapters (flat):    ",
          chap.sort_values("flat_instability", ascending=False).chapter.head(5).tolist())
    print("Most unstable chapters (family):  ",
          chap.sort_values("family_instability", ascending=False).chapter.head(5).tolist())
    print("Deepest between-family disagreement:",
          chap.sort_values("between_family_split", ascending=False).chapter.head(5).tolist())


if __name__ == "__main__":
    main()
