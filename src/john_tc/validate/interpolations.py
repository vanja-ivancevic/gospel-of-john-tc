"""Hard validation gate: known interpolations must register as coverage troughs.

The discarded variant-density metric FAILED this — the Pericope Adulterae (John 7:53-8:11),
the textbook late interpolation, came out *less* variable than its context. The rebuilt
presence/absence metric (extant base manuscripts per verse) must show the opposite:
PA verses attested by significantly FEWER manuscripts than the rest of John.

A one-sided permutation test on the difference of mean coverage gives a distribution-free
p-value; the gate asserts both direction and significance.
"""
from __future__ import annotations

import numpy as np

from john_tc.config import load_config
from john_tc.metrics.instability import verse_metrics


def permutation_lower(target_ids: list[str], df, value_col: str, seed: int,
                      n_perm: int = 10000) -> dict:
    """One-sided test: is the mean of `value_col` over target verses LOWER than the rest?"""
    mask = df["verse_id"].isin(target_ids)
    target = df.loc[mask, value_col].to_numpy(dtype=float)
    rest = df.loc[~mask, value_col].to_numpy(dtype=float)
    obs = target.mean() - rest.mean()  # negative => target lower (the desired direction)
    k = len(target)
    allv = df[value_col].to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    n = len(allv)
    count = 0
    for _ in range(n_perm):
        idx = rng.choice(n, size=k, replace=False)
        diff = allv[idx].mean() - np.delete(allv, idx).mean()
        if diff <= obs:
            count += 1
    p = (count + 1) / (n_perm + 1)
    return dict(
        n_target=k, target_mean=float(target.mean()), rest_mean=float(rest.mean()),
        difference=float(obs), direction_lower=bool(obs < 0), p_value=float(p),
    )


def run_gate(db_path=None, n_perm: int | None = None) -> dict:
    cfg = load_config()
    seed = cfg["seed"]
    n_perm = n_perm or cfg["stats"]["n_permutations"]
    df = verse_metrics(db_path)
    results = {}
    for label, ids in [
        ("pericope_adulterae", cfg["validation"]["pericope_adulterae"]),
        ("known_interpolations", cfg["validation"]["known_interpolations"]),
    ]:
        ids = [v for v in ids if v in set(df["verse_id"])]
        if not ids:
            results[label] = {"skipped": "no verses present"}
            continue
        r = permutation_lower(ids, df, "extant_base_ms", seed=seed, n_perm=n_perm)
        r["verses_present"] = ids
        # Gate passes when coverage is lower (omitted) and significant.
        r["passed"] = bool(r["direction_lower"] and r["p_value"] < cfg["stats"]["fdr_alpha"])
        results[label] = r
    results["gate_passed"] = bool(results["pericope_adulterae"].get("passed"))
    return results


def main() -> None:
    res = run_gate()
    for k, v in res.items():
        if k == "gate_passed":
            continue
        if v.get("skipped"):
            print(f"{k}: SKIPPED ({v['skipped']})")
            continue
        print(f"\n{k}: {'PASS' if v.get('passed') else 'FAIL'}")
        print(f"  target coverage {v['target_mean']:.1f} vs rest {v['rest_mean']:.1f} MS "
              f"(Δ={v['difference']:.1f}, p={v['p_value']:.4g}, n={v['n_target']})")
    print(f"\nVALIDATION GATE: {'PASSED' if res['gate_passed'] else 'FAILED'}")


if __name__ == "__main__":
    main()
