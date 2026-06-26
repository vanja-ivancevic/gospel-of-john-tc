"""RQ2 — does textual instability track CONFOUNDS rather than 'section'?

A section can look more variable for mundane reasons, so control for the ordinary drivers of
variation before reading anything into it:

  coverage       - how many witnesses attest the verse (sampling)
  verse_length   - longer verses have more opportunities to vary
  n_lectionaries - lectionary/liturgical transmission (frequently-read text)
  synoptic       - verses with Synoptic parallels invite harmonisation

Then ask whether a 'section' indicator (Prologue / Farewell / ch21 appendix vs body) adds
anything beyond the confounds. Unit of analysis = verse (no per-unit pseudo-replication),
OLS with HC3 robust SE, Benjamini-Hochberg FDR, and a robust Wald test for section's joint effect.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from john_tc.config import load_config

# John pericopes with Synoptic parallels (Aland, Synopsis Quattuor Evangeliorum).
SYNOPTIC_RANGES = [
    (1, 19, 34), (2, 13, 22), (6, 1, 21), (12, 1, 8), (12, 12, 19),
    (13, 21, 30), (18, 1, 40), (19, 1, 42),
]


def _section(chapter: int, verse: int) -> str:
    if chapter == 1 and verse <= 18:
        return "prologue"
    if 13 <= chapter <= 17:
        return "farewell"
    if chapter == 21:
        return "appendix"
    return "body"


def _is_synoptic(chapter: int, verse: int) -> bool:
    return any(c == chapter and a <= verse <= b for c, a, b in SYNOPTIC_RANGES)


def build_verse_table(db_path: Path | None = None) -> pd.DataFrame:
    from john_tc.metrics.instability import verse_metrics

    cfg = load_config()
    db_path = db_path or cfg.path("collation_db")
    con = duckdb.connect(str(db_path), read_only=True)
    vlen = con.execute("""SELECT verse_id, max(app_to) AS verse_length
                          FROM units WHERE app_type='main' GROUP BY 1""").df()
    nlect = con.execute("""SELECT u.verse_id, count(DISTINCT a.base_ga) AS n_lectionaries
        FROM units u JOIN readings r ON r.app_id=u.app_id
        JOIN attestation a ON a.app_id=r.app_id AND a.reading_id=r.reading_id
        WHERE u.app_type='main' AND a.base_ga LIKE 'L%' AND r.reading_type IS DISTINCT FROM 'lac'
        GROUP BY 1""").df()
    fam = con.execute("""SELECT verse_id, avg(family_instability) AS family_instability,
                                avg(CAST(between_family_split AS DOUBLE)) AS between_family_split,
                                count(*) AS n_units_fam
                         FROM metrics_unit_family GROUP BY 1""").df()
    # genealogical breadth per verse: between_family_split mechanically rises with how many
    # families are co-extant, so n_families must be a control (not just raw coverage).
    conf = con.execute("""
        WITH att AS (SELECT DISTINCT u.verse_id, a.base_ga FROM units u JOIN readings r ON r.app_id=u.app_id
            JOIN attestation a ON a.app_id=r.app_id AND a.reading_id=r.reading_id
            WHERE u.app_type='main' AND r.reading_type IS DISTINCT FROM 'lac' AND a.base_ga<>'basetext')
        SELECT v.verse_id, count(DISTINCT coalesce(m.family,'other')) AS n_families
        FROM att v LEFT JOIN witness_metadata m ON m.base_ga=v.base_ga GROUP BY 1""").df()
    con.close()

    v = verse_metrics(db_path)[["chapter", "verse", "verse_id", "extant_base_ms"]]
    df = (v.merge(vlen, on="verse_id").merge(nlect, on="verse_id", how="left")
            .merge(fam, on="verse_id", how="left").merge(conf, on="verse_id", how="left"))
    df["n_lectionaries"] = df["n_lectionaries"].fillna(0)
    df = df.dropna(subset=["between_family_split"])
    df["coverage"] = df["extant_base_ms"]
    df["synoptic"] = df.apply(lambda r: int(_is_synoptic(r.chapter, r.verse)), axis=1)
    df["section"] = df.apply(lambda r: _section(r.chapter, r.verse), axis=1)
    return df


def _z(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std(ddof=0)


_CONTROLS = ["coverage_z", "verse_length_z", "n_lectionaries_z", "n_families_z"]


def run(dv: str = "between_family_split", db_path: Path | None = None) -> dict:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    from statsmodels.stats.multitest import multipletests
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    df = build_verse_table(db_path).copy()
    for c in ["coverage", "verse_length", "n_lectionaries", "n_families"]:
        df[c + "_z"] = _z(df[c])
    ctrl = " + ".join(_CONTROLS)
    full_f = f"{dv} ~ {ctrl} + synoptic + C(section, Treatment('body'))"
    red_f = f"{dv} ~ {ctrl} + synoptic"
    full = smf.ols(full_f, data=df).fit(cov_type="HC3")
    red = smf.ols(red_f, data=df).fit(cov_type="HC3")

    coefs = full.params.drop("Intercept")
    pvals = full.pvalues.drop("Intercept")
    fdr = multipletests(pvals.values, method="fdr_bh")[1]
    table = pd.DataFrame({"coef": coefs.values, "p": pvals.values, "p_fdr": fdr},
                         index=coefs.index).round(4)
    # Does 'section' add signal beyond confounds? Robust Wald test on the section dummies
    # (valid under HC3, unlike an F-test on nested models).
    section_terms = [t for t in full.params.index if "section" in t]
    R = np.zeros((len(section_terms), len(full.params)))
    for i, t in enumerate(section_terms):
        R[i, full.params.index.get_loc(t)] = 1.0
    wald = full.wald_test(R, use_f=False, scalar=True)
    section_p = float(np.squeeze(wald.pvalue))

    # collinearity diagnostics (HC3 SEs inflate under collinearity; report VIFs)
    Xv = df[_CONTROLS + ["synoptic"]].assign(_const=1.0)
    vif = {c: round(float(variance_inflation_factor(Xv.values, i)), 2)
           for i, c in enumerate(Xv.columns) if c != "_const"}
    # functional-form sensitivity: the DV is a bounded proportion, so refit as a fractional
    # (quasi-binomial logit) GLM weighted by units/verse, and confirm the focal signs/significance
    # survive. (OLS+HC3 stays the headline for interpretability.)
    glm_focal = {}
    try:
        glm = smf.glm(full_f, data=df, family=sm.families.Binomial(),
                      var_weights=df["n_units_fam"].clip(lower=1)).fit()
        for t in ["synoptic", *section_terms]:
            glm_focal[t] = {"coef": round(float(glm.params[t]), 4),
                            "p": round(float(glm.pvalues[t]), 4)}
    except Exception as e:  # pragma: no cover - GLM is a sensitivity check only
        glm_focal = {"error": str(e)}

    focal_p = {t: float(pvals[t]) for t in ["synoptic", *section_terms]}
    return {
        "dv": dv, "n": int(len(df)),
        "r2_full": round(full.rsquared, 4), "r2_reduced": round(red.rsquared, 4),
        "section_wald_chi2": round(float(np.squeeze(wald.statistic)), 3), "section_p": section_p,
        "section_adds_signal": bool(section_p < 0.05),
        "coefficients": table, "vif": vif, "focal_p": focal_p, "glm_focal": glm_focal,
    }


def write_report(path: Path | None = None, db_path: Path | None = None) -> Path:
    cfg = load_config()
    path = path or cfg.path("reports") / "analysis" / "CONFOUNDS.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    from statsmodels.stats.multitest import multipletests

    L = ["# RQ2 — confound-controlled regression of textual instability", "",
         "Controls: coverage, verse length, lectionary use, **and number of families** (the "
         "between-family-split outcome mechanically rises with how many families are co-extant, so "
         "family count is a confound, not just raw coverage). OLS with HC3 robust SEs is the "
         "headline; a fractional quasi-binomial logit GLM is reported as a functional-form "
         "sensitivity check (the outcome is a bounded proportion).", ""]
    results = {}
    for dv in ("between_family_split", "family_instability"):
        r = run(dv, db_path)
        results[dv] = r
        L += [f"## DV: {dv}  (n={r['n']} verses)", "",
              f"- R² full = {r['r2_full']}, R² confounds-only = {r['r2_reduced']}",
              f"- Section adds signal beyond confounds? **{r['section_adds_signal']}** "
              f"(Wald χ²={r['section_wald_chi2']}, p={r['section_p']:.4g})",
              f"- VIF (collinearity): {r['vif']}", "",
              "| predictor | coef (β) | p | p (FDR, within model) |", "|--|--|--|--|"]
        for name, row in r["coefficients"].iterrows():
            L.append(f"| {name} | {row.coef:+.4f} | {row.p:.4g} | {row.p_fdr:.4g} |")
        if isinstance(r["glm_focal"], dict) and "error" not in r["glm_focal"]:
            L += ["", "GLM (fractional logit) sensitivity on focal terms: "
                  + ", ".join(f"{t}: β={d['coef']:+.3f}, p={d['p']:.3g}"
                              for t, d in r["glm_focal"].items())]
        L.append("")
    # Correct multiple-testing family: the FOCAL hypotheses (synoptic + section terms) across BOTH
    # outcomes, BH-corrected together — not per-coefficient within a single model.
    pool = [(dv, t, p) for dv, r in results.items() for t, p in r["focal_p"].items()]
    if pool:
        fdr = multipletests([p for _, _, p in pool], method="fdr_bh")[1]
        L += ["## Focal hypotheses — FDR across both outcomes (the correct test family)", "",
              "| outcome | term | p | p (FDR) | survives |", "|--|--|--|--|--|"]
        for (dv, t, p), q in zip(pool, fdr):
            L.append(f"| {dv} | {t} | {p:.4g} | {q:.4g} | {'yes' if q < 0.05 else 'no'} |")
        L.append("")
    path.write_text("\n".join(L), encoding="utf-8")
    return path


def main() -> None:
    for dv in ("between_family_split", "family_instability"):
        r = run(dv)
        print(f"\n=== DV: {dv} (n={r['n']}) ===")
        print(f"R2 full={r['r2_full']}  R2 confounds-only={r['r2_reduced']}  "
              f"section adds signal: {r['section_adds_signal']} "
              f"(Wald χ²={r['section_wald_chi2']}, p={r['section_p']:.4g})")
        print(r["coefficients"].to_string())
    print("\nReport:", write_report())


if __name__ == "__main__":
    main()
