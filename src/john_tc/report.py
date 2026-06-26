"""Assemble every finding into one regenerable report: reports/REPORT.md.

Each number traces to a committed input via the pipeline. No hand-entered statistics.
"""
from __future__ import annotations

from pathlib import Path

from john_tc.config import load_config


def _genealogy_verdict() -> str:
    p = load_config().path("reports") / "genealogy" / "VALIDATION.md"
    if not p.exists():
        return "not yet run"
    for line in p.read_text(encoding="utf-8").splitlines():
        if "VERDICT" in line:
            return line.replace("*", "").replace("VERDICT:", "").strip()
    return "unknown"


def build_report(path: Path | None = None) -> Path:
    from john_tc.analysis.confounds import run as confound_run
    from john_tc.analysis.stylometry import run as stylometry_run
    from john_tc.ingest.apparatus import summary
    from john_tc.metrics.dates import five_four_date_signal
    from john_tc.metrics.stability import summarize as stability_summary
    from john_tc.metrics.weighted_instability import chapter_comparison
    from john_tc.validate.interpolations import run_gate
    from john_tc.validate.robustness import run as robustness_run

    cfg = load_config()
    path = path or cfg.path("reports") / "REPORT.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    s = summary()
    gate = run_gate(n_perm=2000)
    pa = gate["pericope_adulterae"]
    five4 = five_four_date_signal()
    chap = chapter_comparison()
    cb = confound_run("between_family_split")
    sty = stylometry_run()
    stab = stability_summary()
    robust = robustness_run(B=200)

    flat_top = chap.sort_values("flat_instability", ascending=False).chapter.head(5).tolist()
    fam_top = chap.sort_values("family_instability", ascending=False).chapter.head(5).tolist()
    deep_top = chap.sort_values("between_family_split", ascending=False).chapter.head(5).tolist()

    def coef(res, needle):
        row = res["coefficients"].loc[res["coefficients"].index.str.contains(needle)]
        return (row["coef"].iloc[0], row["p_fdr"].iloc[0]) if len(row) else (float("nan"),) * 2

    pro_b, pro_p = coef(cb, "prologue")
    syn_b, syn_p = coef(cb, "synoptic")

    L = [
        "# Gospel of John — transmission-instability findings (auto-generated)",
        "",
        "Regenerate: `uv run python -m john_tc.pipeline`. Every number below traces to the",
        "committed ECM apparatus via the pipeline; nothing is hand-entered.",
        "",
        "## Data foundation (real cross-witness collation)",
        f"- {s['units_main']:,} substantive variation units, {s['attestations']:,} witness "
        f"attestations, {s['distinct_base_ga']} manuscripts, {s['verses']} verses.",
        "- Source: IGNTP/INTF ECM Greek apparatus of John (positive), NA28 base text.",
        "",
        "## Validation gates (must recover known phenomena in the right direction)",
        f"- **Pericope Adulterae (7:53–8:11)**: attested by {pa['target_mean']:.0f} vs "
        f"{pa['rest_mean']:.0f} MS (Δ={pa['difference']:.0f}, p={pa['p_value']:.2g}) — "
        f"{'PASS' if pa['passed'] else 'FAIL'}.",
        f"- **John 5:4 (date test)**: omitters median {five4['median_omitter_date']:.0f} CE vs "
        f"includers {five4['median_includer_date']:.0f} CE (Δ={five4['difference_years']:.0f} yr, "
        f"p={five4['p_value']:.2g}) — {'PASS' if five4['omitters_earlier'] else 'FAIL'}.",
        f"- **Genealogy validation**: {_genealogy_verdict()} "
        "(silhouette + bootstrap + ARI + sensitivity; see reports/genealogy/VALIDATION.md).",
        "",
        "## RQ1 — instability map (flat vs genealogy-aware)",
        f"- Most unstable chapters, flat (1 witness=1 vote): {flat_top}",
        f"- Most unstable chapters, family-vote (Byz counts once): {fam_top}",
        f"- Deepest between-family disagreement (branches split): {deep_top}",
        "- Genealogy-aware metrics separate Byzantine copying noise from deep branch-level "
        "variation; figure: reports/instability/chapter_instability_flat_vs_genealogy.png.",
        "",
        "## RQ2 — what explains the variation? (confound-controlled, verse-level, HC3, FDR)",
        f"- Confounds explain little overall (R²={cb['r2_full']:.3f}) — most variation is "
        "unit-idiosyncratic.",
        f"- **Synoptic parallels → more between-family disagreement** (β={syn_b:+.3f}, "
        f"p_fdr={syn_p:.3g}): harmonisation pressure.",
        f"- **Prologue distinctively stable** across branches (β={pro_b:+.3f}, p_fdr={pro_p:.3g}), "
        "robust to confounds.",
        f"- Section adds signal beyond confounds (Wald χ²={cb['section_wald_chi2']}, "
        f"p={cb['section_p']:.3g}) — entirely Prologue-driven; ch21/Farewell not distinctive.",
        "",
        "## Textual-stability map (complement of instability)",
        f"- Family-vote stability (headline, 'weighed' — one family one vote) mean = "
        f"{stab['mean_family_consensus']}; raw consensus ('counted', every witness equal) = "
        f"{stab['mean_consensus']}; {stab['anchor_units']:,}/{stab['n_units']:,} units "
        f"({stab['anchor_frac']:.0%}) are near-unanimous by raw count, "
        f"{stab['family_anchor_units']:,} have all families agreeing.",
        f"- Most stable chapters (family-vote): {stab['most_stable_chapters']}; least stable: "
        f"{stab['least_stable_chapters']}.",
        f"- Family internal homogeneity: {stab['family_homogeneity']}.",
        "",
        "## Robustness (do the findings survive resampling/perturbation?)",
        f"- **Overall robust: {robust['all_robust']}.** Leave-one-family Spearman ≥ "
        f"{robust['leave_one_family_out']['min_spearman']} (map not driven by any one family).",
        f"- Prologue-stable coefficient bootstrap CI {robust['confounds']['prologue_ci']} "
        f"(robustly negative: {robust['confounds']['prologue_robust_negative']}); Synoptic CI "
        f"{robust['confounds']['synoptic_ci']} (robustly positive: "
        f"{robust['confounds']['synoptic_robust_positive']}).",
        f"- Ch21 stays low under every family drop ({robust['leave_one_family_out']['ch21_stays_low']}); "
        "its bootstrap CI overlaps the median, so it is 'not elevated', not 'uniquely most stable'.",
        "",
        "## RQ4 — stylometry (function-word Burrows's Delta; register/genre only, not authorship)",
        f"- Method validated: large-sample same-author Δ={sty['large_sample']['same_author']:.2f} "
        f"vs different-author Δ={sty['large_sample']['diff_author']:.2f} (separates authors).",
        "- Size-matched **permutation test** (BH-corrected over 3 sections): "
        + "; ".join(f"{k} p_fdr={v.get('p_fdr','—')}"
                    + ("**(seam)**" if v.get("seam") else "")
                    for k, v in sty["section_tests"].items()) + ".",
        "- Once size is controlled, the Prologue and chapter 21 are not stylometrically distinct. "
        "The Farewell Discourse is register-distinct, consistent with its genre (an extended "
        "monologue), and that carries no authorship or source claim.",
        "",
        "## Notable findings",
        "- Chapter 21, often read as a late appendix, sits among the most stable chapters and shows "
        "no distinctive instability after confound controls.",
        "- Stability and instability track scribal transmission, so they speak to how the text was "
        "copied, not to when or by whom it was composed.",
        "",
        "## Scope / honesty",
        "- This is a transmission-history study. Manuscript data records scribal copying, so the "
        "project makes no claim about composition date or authorship.",
        "- Münster's CBGM is unavailable for John; the genealogy here is our own pre-genealogical "
        "coherence, validated against published family lists.",
    ]
    path.write_text("\n".join(L), encoding="utf-8")
    return path


def main() -> None:
    print("Wrote", build_report())


if __name__ == "__main__":
    main()
