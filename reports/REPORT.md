# Gospel of John — transmission-instability findings (auto-generated)

Regenerate: `uv run python -m john_tc.pipeline`. Every number below traces to the
committed ECM apparatus via the pipeline; nothing is hand-entered.

## Data foundation (real cross-witness collation)
- 10,947 substantive variation units, 1,530,450 witness attestations, 215 manuscripts, 879 verses.
- Source: IGNTP/INTF ECM Greek apparatus of John (positive), NA28 base text.

## Validation gates (must recover known phenomena in the right direction)
- **Pericope Adulterae (7:53–8:11)**: attested by 79 vs 139 MS (Δ=-60, p=0.0015) — PASS.
- **John 5:4 (date test)**: omitters median 449 CE vs includers 1049 CE (Δ=-600 yr, p=0.0001) — PASS.
- **Genealogy validation**: PASSED (silhouette + bootstrap + ARI + sensitivity; see reports/genealogy/VALIDATION.md).

## RQ1 — instability map (flat vs genealogy-aware)
- Most unstable chapters, flat (1 witness=1 vote): [10, 9, 19, 13, 14]
- Most unstable chapters, family-vote (Byz counts once): [9, 14, 19, 12, 17]
- Deepest between-family disagreement (branches split): [19, 9, 13, 18, 6]
- Genealogy-aware metrics separate Byzantine copying noise from deep branch-level variation; figure: reports/instability/chapter_instability_flat_vs_genealogy.png.

## RQ2 — what explains the variation? (confound-controlled, verse-level, HC3, FDR)
- Confounds explain little overall (R²=0.036) — most variation is unit-idiosyncratic.
- **Synoptic parallels → more between-family disagreement** (β=+0.033, p_fdr=0.0075): harmonisation pressure.
- **Prologue distinctively stable** across branches (β=-0.075, p_fdr=0.0023), robust to confounds.
- Section adds signal beyond confounds (Wald χ²=13.358, p=0.00392) — entirely Prologue-driven; ch21/Farewell not distinctive.

## Textual-stability map (complement of instability)
- Family-vote stability (headline, 'weighed' — one family one vote) mean = 0.962; raw consensus ('counted', every witness equal) = 0.959; 6,752/10,605 units (64%) are near-unanimous by raw count, 9,304 have all families agreeing.
- Most stable chapters (family-vote): [15, 17, 3, 5, 1]; least stable: [19, 10, 6, 18, 13].
- Family internal homogeneity: {'f1': 0.745, 'f13': 0.833, 'Byz': 0.631, 'Alexandrian': 0.667}.

## Robustness (do the findings survive resampling/perturbation?)
- **Overall robust: True.** Leave-one-family Spearman ≥ 0.929 (map not driven by any one family).
- Prologue-stable coefficient bootstrap CI (-0.0901, -0.0615) (robustly negative: True); Synoptic CI (0.0128, 0.0473) (robustly positive: True).
- Ch21 stays low under every family drop (True); its bootstrap CI overlaps the median, so it is 'not elevated', not 'uniquely most stable'.

## RQ4 — stylometry (function-word Burrows's Delta; register/genre only, not authorship)
- Method validated: large-sample same-author Δ=0.75 vs different-author Δ=1.30 (separates authors).
- Size-matched **permutation test** (BH-corrected over 3 sections): prologue p_fdr=0.1038; farewell p_fdr=0.0006**(seam)**; ch21 p_fdr=0.7399.
- Once size is controlled, the Prologue and chapter 21 are not stylometrically distinct. The Farewell Discourse is register-distinct, consistent with its genre (an extended monologue), and that carries no authorship or source claim.

## Notable findings
- Chapter 21, often read as a late appendix, sits among the most stable chapters and shows no distinctive instability after confound controls.
- Stability and instability track scribal transmission, so they speak to how the text was copied, not to when or by whom it was composed.

## Scope / honesty
- This is a transmission-history study. Manuscript data records scribal copying, so the project makes no claim about composition date or authorship.
- Münster's CBGM is unavailable for John; the genealogy here is our own pre-genealogical coherence, validated against published family lists.