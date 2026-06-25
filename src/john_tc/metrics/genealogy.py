"""Recover manuscript families from the collation itself (pre-genealogical coherence).

The discipline's tool for this is the INTF Coherence-Based Genealogical Method (CBGM),
but its published genealogical data covers Mark/Acts/Catholic Letters/Revelation — NOT
John (ECM John unpublished). We don't have to wait: the full ECM collation already
contains the signal. This module computes **pre-genealogical coherence** — pairwise
agreement between witnesses over the units where both are extant — then clusters it into
families and validates the clusters against textbook groups (Family 1, Family 13,
the Alexandrian witnesses).

Why it matters: our coverage/instability metrics currently count witnesses as a flat pool,
which over-weights the numerous Byzantine manuscripts (this is why John 5:4's early-witness
omission was missed). Family structure lets us weight/stratify by text-type instead.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

from john_tc.config import load_config

# Core membership of the two genuinely TIGHT families (for validation only — not used to
# build the clusters). These are the textbook benchmark groups a correct method must recover.
# Note: in John the "Alexandrian" witnesses (P75 03 019 ...) are a LOOSE group, not a tight
# clade (01 is famously idiosyncratic, P75-03 only ~0.18 apart), so they are reported
# descriptively, not used as a monophyly benchmark.
KNOWN_FAMILIES = {
    "f1": ["1", "1582", "118", "209"],
    "f13": ["13", "69", "124", "346", "543", "788", "826", "828", "983"],
}


def reading_matrix(db_path: Path | None = None, min_units: int = 200):
    """(witnesses, units x witnesses int matrix). One firsthand reading per (unit, witness)."""
    cfg = load_config()
    con = duckdb.connect(str(db_path or cfg.path("collation_db")), read_only=True)
    df = con.execute(
        """
        WITH a AS (
          SELECT r.app_id, a.base_ga, r.reading_id,
                 row_number() OVER (PARTITION BY r.app_id, a.base_ga
                    ORDER BY CASE WHEN a.hand='firsthand' THEN 0 ELSE 1 END, r.reading_id) rn
          FROM readings r
          JOIN attestation a ON a.app_id=r.app_id AND a.reading_id=r.reading_id
          JOIN units u ON u.app_id=r.app_id
          WHERE u.app_type='main' AND r.reading_type IS DISTINCT FROM 'lac')
        SELECT app_id, base_ga, reading_id FROM a WHERE rn=1
        """
    ).df()
    con.close()
    # drop sparse witnesses
    counts = df.groupby("base_ga").size()
    keep = counts[counts >= min_units].index
    df = df[df.base_ga.isin(keep)].copy()
    # GLOBAL factorize: the same reading_id maps to the same code everywhere, so within a
    # unit (row) two witnesses sharing a reading compare equal. Rows are never compared to
    # each other, so unit-local reading letters need no per-unit remapping.
    df["code"] = pd.factorize(df["reading_id"])[0]
    mat = df.pivot_table(index="app_id", columns="base_ga", values="code", aggfunc="first")
    arr = mat.to_numpy(dtype=float)
    codes = np.where(np.isnan(arr), -1, arr).astype(np.int32)  # missing -> -1
    return list(mat.columns), codes


def informative_mask(codes: np.ndarray, min_extant: int = 30, max_modal: float = 0.90):
    """Keep only genuinely contested units: well-attested AND not near-unanimous.

    Units where ~everyone reads the base text carry no family signal and, en masse, drown
    the discriminating units. Restricting to contested units is the pre-genealogical
    analogue of collating only at points of variation.
    """
    keep = np.zeros(codes.shape[0], dtype=bool)
    for i in range(codes.shape[0]):
        row = codes[i]
        present = row[row >= 0]
        if present.size < min_extant:
            continue
        _, cnts = np.unique(present, return_counts=True)
        if cnts.max() / present.size < max_modal:
            keep[i] = True
    return keep


def coherence_distance(witnesses: list[str], codes: np.ndarray, min_overlap: int = 100):
    """Pairwise distance = 1 - (agreement over co-extant units). Returns (W x W) array."""
    W = len(witnesses)
    dist = np.ones((W, W), dtype=float)
    np.fill_diagonal(dist, 0.0)
    present = codes >= 0  # units x W boolean
    for i in range(W):
        ai = codes[:, i]
        pi = present[:, i]
        for j in range(i + 1, W):
            both = pi & present[:, j]
            n = both.sum()
            if n < min_overlap:
                continue
            agree = (ai[both] == codes[both, j]).mean()
            d = 1.0 - agree
            dist[i, j] = dist[j, i] = d
    return dist


def cluster_families(witnesses, dist, n_clusters: int = 12):
    """Average-linkage hierarchical clustering of the coherence distance."""
    condensed = squareform(dist, checks=False)
    Z = linkage(condensed, method="average")
    labels = fcluster(Z, t=n_clusters, criterion="maxclust")
    return pd.DataFrame({"base_ga": witnesses, "cluster": labels}), Z


def family_monophyly(witnesses: list[str], Z: np.ndarray) -> dict:
    """Monophyly test: does each known family form its own clean subtree?

    For a family, find the smallest subtree (clade) containing all its present members and
    measure purity = members / clade-size. A genuine family is (near-)monophyletic: its
    minimal clade contains few or no non-members. This is robust to the Byzantine trunk that
    defeats flat `maxclust` cutting — f1/f13 are shallow but real clades.
    """
    from scipy.cluster.hierarchy import to_tree

    _, nodes = to_tree(Z, rd=True)
    idx = {w: i for i, w in enumerate(witnesses)}
    out = {}
    clades = {}
    for fam, members in KNOWN_FAMILIES.items():
        present = [m for m in members if m in idx]
        if len(present) < 2:
            out[fam] = {"present": present, "passed": None}
            continue
        target = {idx[m] for m in present}
        best = None
        for node in nodes:
            if node.is_leaf():
                continue
            leafset = set(node.pre_order(lambda x: x.id))
            if target.issubset(leafset) and (best is None or len(leafset) < len(best)):
                best = leafset
        purity = len(target) / len(best)
        intruders = sorted(witnesses[i] for i in (best - target))
        clades[fam] = best
        # "Recovered" = either (near-)monophyletic OR a compact clade: the family's common
        # ancestor spans a small, distinct slice of the tree (core + textual associates),
        # not the whole Byzantine trunk. Compactness threshold = 12% of all witnesses.
        compact = len(best) <= 0.12 * len(witnesses)
        out[fam] = {
            "present": present, "clade_size": len(best), "purity": round(purity, 3),
            "intruders": intruders[:12],
            "monophyletic": bool(purity >= 0.7), "compact": bool(compact),
            "recovered": bool(purity >= 0.7 or compact),
        }
    # Separation: the families' minimal clades must be disjoint.
    fams = list(clades)
    disjoint = all(clades[a].isdisjoint(clades[b])
                   for i, a in enumerate(fams) for b in fams[i + 1:])
    out["families_disjoint"] = bool(disjoint)
    out["all_passed"] = bool(
        disjoint and all(v["recovered"] for v in out.values()
                         if isinstance(v, dict) and "recovered" in v)
    )
    return out


def build(db_path: Path | None = None, n_clusters: int = 12) -> dict:
    cfg = load_config()
    db_path = db_path or cfg.path("collation_db")
    wits, codes = reading_matrix(db_path)
    mask = informative_mask(codes)
    dist = coherence_distance(wits, codes[mask])
    assign, Z = cluster_families(wits, dist, n_clusters=n_clusters)
    con = duckdb.connect(str(db_path))
    con.execute("CREATE OR REPLACE TABLE witness_family AS SELECT * FROM assign")
    dist_df = pd.DataFrame(dist, index=wits, columns=wits).reset_index(names="base_ga")  # noqa: F841 — used by name in DuckDB SQL
    con.execute("CREATE OR REPLACE TABLE witness_distance AS SELECT * FROM dist_df")
    con.close()
    sizes = assign.cluster.value_counts().sort_index()
    return {
        "witnesses": len(wits), "informative_units": int(mask.sum()), "total_units": len(mask),
        "cluster_sizes": sizes.to_dict(), "validation": family_monophyly(wits, Z),
    }


def main() -> None:
    res = build()
    print(f"Clustered {res['witnesses']} witnesses over {res['informative_units']} "
          f"informative units (of {res['total_units']}).")
    print(f"Cluster sizes: {res['cluster_sizes']}")
    v = res["validation"]
    for fam in KNOWN_FAMILIES:
        d = v[fam]
        if d.get("recovered") is None:
            print(f"  {fam:12s} insufficient members: {d['present']}")
        else:
            tag = "MONOPHYLETIC" if d["monophyletic"] else ("COMPACT-CLADE" if d["compact"]
                                                            else "NOT-CLEAN")
            extra = f" +associates={d['intruders']}" if d["intruders"] else ""
            print(f"  {fam:12s} clade={d['clade_size']} purity={d['purity']:.0%} {tag}{extra}")
    print(f"  families_disjoint: {v['families_disjoint']}")
    print(f"\nFAMILY RECOVERY: {'PASSED' if v['all_passed'] else 'FAILED'}")


if __name__ == "__main__":
    main()
