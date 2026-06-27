"""Family labels + genealogy-aware weighting — the fix for flat 1-witness-1-vote.

The Byzantine majority is ~150 near-identical late copies; counting each as an independent
vote over-weights one late text-form and buries early/independent evidence (the John 5:4
problem). Here we attach a family to every witness and provide family-aware weights so the
Byzantine block counts as roughly one genealogical voice, not 150.

Family membership provenance is always tracked (`family_source`):
  - iohannes_list : asserted by the published IGNTP "iohannes" ECM family collations (CC BY 4.0)
  - manual        : the (loose) Alexandrian early group, by scholarly consensus
  - computed      : assigned from our own pre-genealogical clustering (Byzantine mass / other)
Asserted membership is never silently mixed with computed.

Family scholarship credited:
  - Family 1 in John: the IGNTP "iohannes" family collation; Welsby, *A Textual Study of Family 1
    in the Gospel of John* (ANTF 45, De Gruyter 2014; open-access Birmingham PhD, etheses 3338) is
    the definitive study and isolates the 1+1582 core and the 565+884+2193 sub-group.
  - Family 13 in John: Perrin, *Family 13 in St John's Gospel* (NTTSD 58, Brill 2018) — our list
    matches his continuous-text membership exactly.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from john_tc.config import load_config
from john_tc.metrics.genealogy import cluster_families, coherence_distance, informative_mask, reading_matrix

# Family 1: published IGNTP "iohannes" family collation (https://itseeweb.cal.bham.ac.uk/iohannes/);
# Welsby 2014 (ANTF 45) is the definitive study and refines the core to 1+1582 and 565+884+2193.
#   (Welsby's core sub-groups within f1: the 1+1582 primary pair and the 565+884+2193 rival group.)
# Listed are only the f1 members actually collated in our ECM apparatus set. The published f1 is
# larger (Welsby 2014 / IGNTP iohannes also include GA 131, 205, 872), but those three carry no
# attestation in the apparatus we ingest, so naming them here would assert a member that cannot vote.
OFFICIAL_F1 = ["1", "22", "118", "138", "209", "357", "565", "884", "994", "1192",
               "1210", "1278", "1582", "2193", "2372", "2575", "2713", "2886"]
# Family 13: matches Perrin 2018 (NTTSD 58) continuous-text membership for John exactly.
OFFICIAL_F13 = ["13", "69", "124", "346", "543", "788", "826", "828", "983", "1689"]
# Early "Alexandrian" group — loose in John (consensus, not a tight clade): primary witnesses.
ALEXANDRIAN_CORE = ["P66", "P75", "01", "03", "019", "04", "032"]


def assign_families(db_path: Path | None = None) -> pd.DataFrame:
    """One row per witness: base_ga, family, family_source."""
    geneal = load_config()["genealogy"]
    wits, codes = reading_matrix(db_path)
    dist = coherence_distance(wits, codes[informative_mask(codes)])
    assign, _ = cluster_families(wits, dist, n_clusters=geneal["n_clusters"])
    # Dominant mass = Byzantine-and-allies. Total-ordered tie-break (largest, then smallest cluster
    # id) so the label is deterministic when cluster sizes tie -> no more +/-1 family flips.
    sizes = assign.cluster.value_counts().to_dict()
    byz_cluster = sorted(sizes.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    in_byz = set(assign.loc[assign.cluster == byz_cluster, "base_ga"])

    rows = []
    for w in wits:
        if w in OFFICIAL_F1:
            fam, src = "f1", "iohannes_list"
        elif w in OFFICIAL_F13:
            fam, src = "f13", "iohannes_list"
        elif w in ALEXANDRIAN_CORE:
            fam, src = "Alexandrian", "manual"
        elif w in in_byz:
            fam, src = "Byz", "computed"
        else:
            fam, src = "other", "computed"
        rows.append(dict(base_ga=w, family=fam, family_source=src))
    return pd.DataFrame(rows)


def witness_weights(fam: pd.DataFrame) -> pd.DataFrame:
    """weight = 1 / family_size, so each family contributes ~one effective vote.

    'other' witnesses are genealogically isolated -> weight 1 each (full voice).
    """
    sizes = fam.family.value_counts().to_dict()
    fam = fam.copy()
    fam["weight"] = fam.apply(
        lambda r: 1.0 if r.family == "other" else 1.0 / sizes[r.family], axis=1
    )
    return fam


def build(db_path: Path | None = None) -> dict:
    cfg = load_config()
    db_path = db_path or cfg.path("collation_db")
    fam = witness_weights(assign_families(db_path))
    con = duckdb.connect(str(db_path))
    con.execute("CREATE OR REPLACE TABLE witness_metadata AS SELECT * FROM fam")
    con.close()
    return {"witnesses": len(fam), "family_counts": fam.family.value_counts().to_dict()}


def family_support(verse_id: str, db_path: Path | None = None) -> pd.DataFrame:
    """For each reading of a verse: witness count vs DISTINCT-FAMILY count.

    The contrast that catches genealogically-narrow readings: a reading with many witnesses
    but only ONE family (e.g. a Byzantine-only addition) is genealogically weak despite a
    big head-count.
    """
    cfg = load_config()
    con = duckdb.connect(str(db_path or cfg.path("collation_db")), read_only=True)
    df = con.execute(
        """
        SELECT r.app_id, r.reading_id, r.reading_type, r.is_lemma,
               substr(r.reading_text,1,24) AS txt,
               count(DISTINCT a.base_ga) AS n_wit,
               count(DISTINCT m.family) FILTER (WHERE m.family IS NOT NULL) AS n_families,
               string_agg(DISTINCT m.family, ',') AS families
        FROM units u
        JOIN readings r ON r.app_id=u.app_id
        JOIN attestation a ON a.app_id=r.app_id AND a.reading_id=r.reading_id
        LEFT JOIN witness_metadata m ON m.base_ga=a.base_ga
        WHERE u.verse_id=? AND u.app_type='main' AND r.reading_type IS DISTINCT FROM 'lac'
        GROUP BY 1,2,3,4,5 ORDER BY r.app_id, n_wit DESC
        """,
        [verse_id],
    ).df()
    con.close()
    return df


def main() -> None:
    res = build()
    print(f"Assigned families to {res['witnesses']} witnesses:")
    for f, n in sorted(res["family_counts"].items(), key=lambda x: -x[1]):
        print(f"  {f:12s} {n}")


if __name__ == "__main__":
    main()
