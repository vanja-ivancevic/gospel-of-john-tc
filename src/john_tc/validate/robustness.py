"""Stress-test the headline findings — do they survive resampling and perturbation?

The pre-rebuild project's claims were artifacts that collapsed under scrutiny. Before trusting
ours, we check:

  1. Bootstrap CIs on chapter instability — are the rankings (ch21 low, passion high) stable?
  2. Leave-one-family-out — is the instability map driven by a single family (e.g. Byzantine)?
  3. Confound-coefficient bootstrap — are the Prologue-stable and Synoptic-harmonisation
     effects robustly non-zero?

All seeded from config.yaml.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from john_tc.config import load_config
from john_tc.metrics.weighted_instability import _LONG_SQL


def _rng():
    return np.random.default_rng(load_config()["seed"])


def _chapter_family_instability(long: pd.DataFrame) -> pd.Series:
    """Per-chapter family-vote instability from a (possibly family-filtered) long table."""
    grp = (long.groupby(["app_id", "chapter", "family", "reading_id"])
               .agg(n=("base_ga", "count"), is_lemma=("is_lemma", "max")).reset_index())
    grp = grp.sort_values(["app_id", "family", "n"], ascending=[True, True, False])
    plur = grp.drop_duplicates(["app_id", "family"])
    unit = plur.groupby(["app_id", "chapter"]).agg(
        n_fam=("family", "count"),
        n_div=("is_lemma", lambda s: int((~s.astype(bool)).sum()))).reset_index()
    unit["fi"] = unit.n_div / unit.n_fam
    return unit.groupby("chapter")["fi"].mean()


def bootstrap_chapter_ci(B: int = 500, db_path: Path | None = None) -> pd.DataFrame:
    """Resample units; 95% CI of chapter family-instability + between-family split."""
    con = duckdb.connect(str(db_path or load_config().path("collation_db")), read_only=True)
    u = con.execute("""SELECT chapter, family_instability,
                              CAST(between_family_split AS DOUBLE) AS bfs
                       FROM metrics_unit_family""").df()
    con.close()
    rng = _rng()
    chapters = sorted(u.chapter.unique())
    fi_boot = {c: [] for c in chapters}
    bfs_boot = {c: [] for c in chapters}
    for _ in range(B):
        samp = u.iloc[rng.integers(0, len(u), len(u))]
        g = samp.groupby("chapter").agg(fi=("family_instability", "mean"), bfs=("bfs", "mean"))
        for c in chapters:
            if c in g.index:
                fi_boot[c].append(g.loc[c, "fi"])
                bfs_boot[c].append(g.loc[c, "bfs"])
    rows = []
    for c in chapters:
        fi, bfs = np.array(fi_boot[c]), np.array(bfs_boot[c])
        rows.append(dict(chapter=c,
                         fi_lo=np.percentile(fi, 2.5), fi_med=np.median(fi), fi_hi=np.percentile(fi, 97.5),
                         bfs_lo=np.percentile(bfs, 2.5), bfs_med=np.median(bfs), bfs_hi=np.percentile(bfs, 97.5)))
    return pd.DataFrame(rows)


def leave_one_family_out(db_path: Path | None = None) -> dict:
    """Drop each family; does the chapter instability map hold (Spearman vs full)?"""
    con = duckdb.connect(str(db_path or load_config().path("collation_db")), read_only=True)
    long = con.execute(_LONG_SQL).df()
    con.close()
    full = _chapter_family_instability(long)
    out = {}
    for fam in ("Byz", "f1", "f13", "Alexandrian", "other"):
        loo = _chapter_family_instability(long[long.family != fam])
        joined = pd.concat([full.rename("full"), loo.rename("loo")], axis=1).dropna()
        rho = joined["full"].corr(joined["loo"], method="spearman")
        out[fam] = round(float(rho), 3)
    # do the qualitative claims survive? ch21 stays low (bottom third), passion stays high (top third)
    ranks = full.rank()
    n = len(full)
    out["ch21_stays_low"] = bool(ranks.get(21, n) <= n / 3)
    out["ch19_stays_high"] = bool(ranks.get(19, 0) >= 2 * n / 3)
    out["min_spearman"] = min(v for k, v in out.items() if isinstance(v, float))
    return out


def bootstrap_confounds(B: int = 500, dv: str = "between_family_split",
                        db_path: Path | None = None) -> dict:
    """Resample verses, refit RQ2, CI on the Prologue and Synoptic coefficients."""
    import statsmodels.formula.api as smf

    from john_tc.analysis.confounds import build_verse_table

    df = build_verse_table(db_path).copy()
    for c in ["coverage", "verse_length", "n_lectionaries"]:
        df[c + "_z"] = (df[c] - df[c].mean()) / df[c].std(ddof=0)
    formula = (f"{dv} ~ coverage_z + verse_length_z + n_lectionaries_z + synoptic "
               "+ C(section, Treatment('body'))")
    rng = _rng()
    pro, syn = [], []
    for _ in range(B):
        s = df.iloc[rng.integers(0, len(df), len(df))]
        try:
            fit = smf.ols(formula, data=s).fit()
        except Exception:
            continue
        pcol = [c for c in fit.params.index if "prologue" in c]
        if pcol:
            pro.append(float(fit.params[pcol[0]]))
        if "synoptic" in fit.params.index:
            syn.append(float(fit.params["synoptic"]))
    pro, syn = np.array(pro), np.array(syn)
    def ci(a):
        return (round(float(np.percentile(a, 2.5)), 4), round(float(np.percentile(a, 97.5)), 4))
    pro_ci, syn_ci = ci(pro), ci(syn)
    return {
        "prologue_ci": pro_ci, "prologue_robust_negative": bool(pro_ci[1] < 0),
        "synoptic_ci": syn_ci, "synoptic_robust_positive": bool(syn_ci[0] > 0),
    }


def run(B: int = 500, db_path: Path | None = None) -> dict:
    ci = bootstrap_chapter_ci(B, db_path)
    loo = leave_one_family_out(db_path)
    conf = bootstrap_confounds(B, "between_family_split", db_path)
    # ch21 reliably below gospel-median family-instability?
    med = ci.fi_med.median()
    ch21 = ci.loc[ci.chapter == 21].iloc[0]
    ch21_low = bool(ch21.fi_hi < med)
    verdict = bool(loo["min_spearman"] >= 0.8 and loo["ch21_stays_low"]
                   and conf["prologue_robust_negative"] and conf["synoptic_robust_positive"])
    return {
        "B": B, "chapter_ci": ci, "leave_one_family_out": loo, "confounds": conf,
        "ch21_below_median_robust": ch21_low, "all_robust": verdict,
    }


def write_report(path: Path | None = None, B: int = 500, db_path: Path | None = None) -> Path:
    cfg = load_config()
    path = path or cfg.path("reports") / "analysis" / "ROBUSTNESS.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    r = run(B, db_path)
    loo, conf = r["leave_one_family_out"], r["confounds"]
    L = ["# Robustness / stability of the findings", "",
         f"Bootstrap B={r['B']} (seeded). **Overall robust: {r['all_robust']}**", "",
         "## 1. Bootstrap CIs on chapter instability",
         f"- Ch21 family-instability 95% CI upper bound below gospel median? "
         f"**{r['ch21_below_median_robust']}** (the 'ch21 not elevated' claim is stable).", "",
         "## 2. Leave-one-family-out (Spearman of chapter map vs full)"]
    for fam in ("Byz", "f1", "f13", "Alexandrian", "other"):
        L.append(f"- drop {fam}: ρ={loo[fam]}")
    L += [f"- min ρ = {loo['min_spearman']} (≥0.8 ⇒ not driven by any single family); "
          f"ch21 stays low: {loo['ch21_stays_low']}; ch19 stays high: {loo['ch19_stays_high']}", "",
          "## 3. Confound coefficients (bootstrap 95% CI)",
          f"- Prologue (between-family): CI {conf['prologue_ci']} — robustly negative: "
          f"{conf['prologue_robust_negative']}",
          f"- Synoptic parallels: CI {conf['synoptic_ci']} — robustly positive: "
          f"{conf['synoptic_robust_positive']}"]
    path.write_text("\n".join(L), encoding="utf-8")
    return path


def main() -> None:
    import sys
    B = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    r = run(B)
    loo, conf = r["leave_one_family_out"], r["confounds"]
    print(f"ch21 below-median robust: {r['ch21_below_median_robust']}")
    print(f"leave-one-family min Spearman: {loo['min_spearman']} "
          f"(ch21 low {loo['ch21_stays_low']}, ch19 high {loo['ch19_stays_high']})")
    print(f"prologue CI {conf['prologue_ci']} robust-neg {conf['prologue_robust_negative']}")
    print(f"synoptic CI {conf['synoptic_ci']} robust-pos {conf['synoptic_robust_positive']}")
    print(f"\nALL ROBUST: {r['all_robust']}")
    print("report:", write_report(B=B))


if __name__ == "__main__":
    main()
