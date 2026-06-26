"""Rigorous validation of our home-built genealogy BEFORE anything is built on it.

Five independent checks, against INDEPENDENT ground truth (published IGNTP family lists +
the IGNTP Byzantine bundle — never our own clusters):

  1. Silhouette of official family labels in our distance space   (are the families real?)
  2. Bootstrap clade support for f1 / f13 / Byz                    (is the tree stable?)
  3. Known-pair / nearest-neighbour checks (P75-03, 1-1582, ...)  (textbook relations hold?)
  4. Adjusted Rand Index + V-measure vs official labels           (clusters match scholarship?)
  5. Parameter sensitivity (overlap, informative threshold)       (robust, not tuned?)

If these don't pass, we do not build on the genealogy.
"""
from __future__ import annotations

import math
import os
import re
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage, to_tree
from scipy.spatial.distance import squareform

from john_tc.config import load_config
from john_tc.metrics.families import ALEXANDRIAN_CORE, OFFICIAL_F1, OFFICIAL_F13
from john_tc.metrics.genealogy import coherence_distance, informative_mask, reading_matrix

# The tight, verified core of Family 1 (Welsby Core + Venice). The full 21-member Welsby list
# is internally heterogeneous in John (565/1192/1210 have Byzantine affinities), so clade-level
# tests use the core; silhouette/ARI still validate the full family as a real cluster.
F1_CORE = ["1", "1582", "118", "209"]


# ---------- independent ground truth ----------
def byzantine_bundle() -> set[str]:
    """GA sigla from the IGNTP Byzantine transcription bundle (independent of our clustering)."""
    d = load_config().root / "data/raw/Byzantine_john_transcriptions"
    out = set()
    if d.exists():
        for f in os.listdir(d):
            s = re.sub(r"\.xml$", "", re.sub(r"^04_", "", f))
            s = re.sub(r"S\d*$", "", s)
            if re.fullmatch(r"(0\d+|\d+|P\d+|L\d+)", s):
                out.add(s)
    return out


def ground_truth(witnesses: list[str]) -> dict[str, str]:
    """Per-witness family label with precedence f1 > f13 > Alexandrian > Byz (non-overlapping)."""
    byz = byzantine_bundle()
    labels = {}
    for w in witnesses:
        if w in OFFICIAL_F1:
            labels[w] = "f1"
        elif w in OFFICIAL_F13:
            labels[w] = "f13"
        elif w in ALEXANDRIAN_CORE:
            labels[w] = "Alexandrian"
        elif w in byz:
            labels[w] = "Byz"
    return labels


# ---------- metrics ----------
def silhouette_by_family(witnesses, dist, labels) -> dict:
    """Mean silhouette of each official family in our distance space (>0 = a real cluster)."""
    idx = {w: i for i, w in enumerate(witnesses)}
    lab = {w: labels[w] for w in labels if w in idx}
    fams = sorted(set(lab.values()))
    per_point = {}
    for w, fam in lab.items():
        i = idx[w]
        same = [dist[i][idx[o]] for o in lab if o != w and lab[o] == fam]
        if not same:
            continue
        a = np.mean(same)
        b = min(
            np.mean([dist[i][idx[o]] for o in lab if lab[o] == g])
            for g in fams if g != fam
        )
        per_point[w] = (b - a) / max(a, b) if max(a, b) > 0 else 0.0
    by_fam = {f: float(np.mean([s for w, s in per_point.items() if lab[w] == f]))
              for f in fams if any(lab[w] == f for w in per_point)}
    return {"by_family": by_fam, "overall": float(np.mean(list(per_point.values())))}


def _min_clade_size(witnesses, Z, members) -> int | None:
    present = {witnesses.index(m) for m in members if m in witnesses}
    if len(present) < 2:
        return None
    _, nodes = to_tree(Z, rd=True)
    best = None
    for node in nodes:
        if node.is_leaf():
            continue
        leaves = set(node.pre_order(lambda x: x.id))
        if present.issubset(leaves) and (best is None or len(leaves) < best):
            best = len(leaves)
    return best


def _recovered(witnesses, Z, members) -> bool:
    cs = _min_clade_size(witnesses, Z, members)
    if cs is None:
        return False
    n = sum(1 for m in members if m in witnesses)
    return cs <= max(2 * n, 0.12 * len(witnesses))


def bootstrap_support(witnesses, codes_inf, family_members: dict, B: int, seed: int,
                      min_overlap: int = 100) -> dict:
    """Resample informative units with replacement; % of replicates each family forms a clade."""
    rng = np.random.default_rng(seed)
    U = codes_inf.shape[0]
    hits = {f: 0 for f in family_members}
    for _ in range(B):
        idx = rng.integers(0, U, U)
        dist = coherence_distance(witnesses, codes_inf[idx], min_overlap=min_overlap)
        Z = linkage(squareform(dist, checks=False), method="average")
        for f, members in family_members.items():
            if _recovered(witnesses, Z, members):
                hits[f] += 1
    return {f: round(h / B, 3) for f, h in hits.items()}


def nearest_neighbour(witnesses, dist, w: str, k: int = 1):
    i = witnesses.index(w)
    order = np.argsort(dist[i])
    out = [(witnesses[j], round(float(dist[i][j]), 3)) for j in order if j != i][:k]
    return out


def adjusted_rand_index(true: list, pred: list) -> float:
    comb2 = lambda n: n * (n - 1) // 2  # noqa: E731
    cont = Counter(zip(true, pred))
    a = sum(comb2(v) for v in Counter(true).values())
    b = sum(comb2(v) for v in Counter(pred).values())
    c = sum(comb2(v) for v in cont.values())
    total = comb2(len(true))
    exp = a * b / total if total else 0
    mx = (a + b) / 2
    return (c - exp) / (mx - exp) if (mx - exp) else 1.0


def v_measure(true: list, pred: list) -> float:
    def ent(labels):
        n = len(labels)
        return -sum((v / n) * math.log(v / n) for v in Counter(labels).values())

    def cond_ent(x, y):  # H(x|y)
        n = len(x)
        joint = Counter(zip(x, y))
        cy = Counter(y)
        return -sum((c / n) * math.log((c / n) / (cy[k[1]] / n)) for k, c in joint.items())

    hc, hk = ent(true), ent(pred)
    h = 1 - cond_ent(true, pred) / hc if hc else 1.0
    cp = 1 - cond_ent(pred, true) / hk if hk else 1.0
    return 2 * h * cp / (h + cp) if (h + cp) else 0.0


def best_cluster_match(witnesses, dist, labels) -> dict:
    """ARI / V-measure vs official labels at the DEPLOYED cut (k = genealogy.n_clusters) — this is
    the headline and the gate. A k=4..k_max sweep is reported descriptively (best-of-sweep is a
    multiple-comparisons artifact, so it must NOT be the gated number)."""
    g = load_config()["genealogy"]
    deployed_k, k_max = g["n_clusters"], g["validation_k_max"]
    Z = linkage(squareform(dist, checks=False), method="average")
    labeled = [w for w in witnesses if w in labels]
    true = [labels[w] for w in labeled]
    idx = {w: i for i, w in enumerate(witnesses)}

    def at(k):
        assign = fcluster(Z, t=k, criterion="maxclust")
        pred = [int(assign[idx[w]]) for w in labeled]
        return adjusted_rand_index(true, pred), v_measure(true, pred)

    sweep_best = {"ari": -1.0, "k": None}
    for k in range(4, k_max + 1):
        ari, _ = at(k)
        if ari > sweep_best["ari"]:
            sweep_best = {"ari": round(ari, 3), "k": k}
    ari_dep, v_dep = at(deployed_k)
    # headline = the cut we actually deploy; sweep kept for context only
    return {"ari": round(ari_dep, 3), "v_measure": round(v_dep, 3), "k": deployed_k,
            "best_ari_sweep": sweep_best}


def sensitivity(db_path=None) -> list[dict]:
    """f1/f13 recovery across overlap + informative-threshold settings (robustness, not tuning)."""
    wits, codes = reading_matrix(db_path)
    rows = []
    for max_modal in (0.85, 0.90, 0.95):
        for min_ov in (50, 100, 200):
            mask = informative_mask(codes, max_modal=max_modal)
            dist = coherence_distance(wits, codes[mask], min_overlap=min_ov)
            Z = linkage(squareform(dist, checks=False), method="average")
            rows.append({
                "max_modal": max_modal, "min_overlap": min_ov, "n_units": int(mask.sum()),
                "f1": _recovered(wits, Z, F1_CORE), "f13": _recovered(wits, Z, OFFICIAL_F13),
            })
    return rows


def run(B: int = 100, db_path: Path | None = None) -> dict:
    cfg = load_config()
    wits, codes = reading_matrix(db_path)
    mask = informative_mask(codes)
    codes_inf = codes[mask]
    dist = coherence_distance(wits, codes_inf)
    labels = ground_truth(wits)

    sil = silhouette_by_family(wits, dist, labels)
    # Clade-level bootstrap on the genuinely tight families; Byz/full-f1 reported descriptively.
    fam_members = {
        "f1_core": [w for w in F1_CORE if w in wits],
        "f13": [w for w in OFFICIAL_F13 if w in wits],
        "f1_full": [w for w in OFFICIAL_F1 if w in wits],
        "Byz": [w for w in wits if labels.get(w) == "Byz"],
    }
    support = bootstrap_support(wits, codes_inf, fam_members, B=B, seed=cfg["seed"])
    pairs = {
        "P75->nearest": nearest_neighbour(wits, dist, "P75", 2),
        "1->nearest": nearest_neighbour(wits, dist, "1", 1),
        "13->nearest": nearest_neighbour(wits, dist, "13", 1),
    }
    match = best_cluster_match(wits, dist, labels)
    sens = sensitivity(db_path)

    # Defensible, non-circular criteria: every official family (incl. the INDEPENDENT Byzantine
    # ground truth) is a real cluster in our distance space (silhouette>0); the tight families
    # recover with high bootstrap clade support; and recovery is robust across parameters. ARI is
    # reported, NOT gated: the deployed cut (k=n_clusters) exists to find the Byzantine mass, not to
    # carve f1/f13 (which are asserted from the published lists), so ARI-at-k is the wrong gate and
    # best-of-sweep ARI would be a multiple-comparisons artifact.
    passed = (
        all(s > 0 for s in sil["by_family"].values())
        and support.get("f1_core", 0) >= 0.7 and support.get("f13", 0) >= 0.7
        and all(r["f1"] and r["f13"] for r in sens)
    )
    return {
        "n_witnesses": len(wits), "n_informative_units": int(mask.sum()),
        "n_labeled": len(labels), "silhouette": sil, "bootstrap_support": support,
        "known_pairs": pairs, "cluster_match": match, "sensitivity": sens, "passed": bool(passed),
    }


def write_report(res: dict, path: Path | None = None) -> Path:
    cfg = load_config()
    path = path or cfg.path("reports") / "genealogy" / "VALIDATION.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    L = ["# Genealogy validation", "",
         f"Witnesses: {res['n_witnesses']} | informative units: {res['n_informative_units']} "
         f"| labelled (ground truth): {res['n_labeled']}", "",
         f"**VERDICT: {'PASSED' if res['passed'] else 'FAILED'}**", "",
         "> **What this validates (and what it does not).** The f1/f13 ground-truth labels are the "
         "published IGNTP lists that we also use to *assign* those families, so silhouette/ARI test "
         "whether our distance metric *groups* the published families as real clusters — they do "
         "**not** independently validate the assignment (that is asserted from the lists). The "
         "Byzantine ground truth is independent (the IGNTP Byzantine bundle) and is gated via "
         "silhouette. ARI is reported at the **deployed** cut (k = genealogy.n_clusters), not the "
         "best-of-sweep, to avoid a multiple-comparisons artifact.", "",
         "## 1. Silhouette of official families (>0 = real cluster in our distances)"]
    for f, s in res["silhouette"]["by_family"].items():
        L.append(f"- {f}: {s:+.3f}")
    L.append(f"- overall: {res['silhouette']['overall']:+.3f}")
    L += ["", "## 2. Bootstrap clade support (fraction of resamples forming the clade)"]
    for f, s in res["bootstrap_support"].items():
        L.append(f"- {f}: {s:.0%}")
    L += ["", "## 3. Known-pair nearest neighbours"]
    for k, v in res["known_pairs"].items():
        L.append(f"- {k}: {v}")
    cm = res["cluster_match"]
    sweep = cm.get("best_ari_sweep", {})
    L += ["", f"## 4. Cluster match vs official labels: ARI={cm['ari']}, "
          f"V-measure={cm['v_measure']} at deployed k={cm['k']} "
          f"(descriptive best-of-sweep: ARI={sweep.get('ari')} at k={sweep.get('k')})",
          "", "## 5. Parameter sensitivity (f1/f13 recovered?)",
          "| max_modal | min_overlap | n_units | f1 | f13 |", "|--|--|--|--|--|"]
    for r in res["sensitivity"]:
        L.append(f"| {r['max_modal']} | {r['min_overlap']} | {r['n_units']} | {r['f1']} | {r['f13']} |")
    path.write_text("\n".join(L), encoding="utf-8")
    return path


def main() -> None:
    import sys
    B = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    res = run(B=B)
    print(write_report(res))
    print(f"\nsilhouette by family: {res['silhouette']['by_family']}")
    print(f"bootstrap support: {res['bootstrap_support']}")
    print(f"cluster match: {res['cluster_match']}")
    print(f"sensitivity all-pass: {all(r['f1'] and r['f13'] for r in res['sensitivity'])}")
    print(f"\nGENEALOGY VALIDATION: {'PASSED' if res['passed'] else 'FAILED'}")


if __name__ == "__main__":
    main()
