# Gospel of John — transmission-instability findings (auto-generated)

Regenerate: `uv run python -m john_tc.pipeline`. Every number below traces to the
committed ECM apparatus via the pipeline; nothing is hand-entered.

## Data foundation (real cross-witness collation)
- 10,947 substantive variation units, 1,530,450 witness attestations, 215 manuscripts, 879 verses.
- Source: IGNTP/INTF ECM Greek apparatus of John (positive), NA28 base text.

## Validation gates (must recover known phenomena in the right direction)
- **Pericope Adulterae (7:53–8:11)**: attested by 80 vs 140 MS (Δ=-60, p=0.0005) — PASS.
- **John 5:4 (date test)**: omitters median 449 CE vs includers 1049 CE (Δ=-600 yr, p=0.0001) — PASS.
- **Genealogy validation**: PASSED (silhouette + bootstrap + ARI + sensitivity; see reports/genealogy/VALIDATION.md).

## RQ1 — instability map (flat vs genealogy-aware)
- Most unstable chapters, flat (1 witness=1 vote): [9, 10, 19, 14, 13]
- Most unstable chapters, family-vote (Byz counts once): [9, 14, 19, 12, 17]
- Deepest between-family disagreement (branches split): [19, 9, 13, 18, 6]
- Genealogy-aware metrics separate Byzantine copying noise from deep branch-level variation; figure: reports/instability/chapter_instability_flat_vs_genealogy.png.

## RQ2 — what explains the variation? (confound-controlled, verse-level, HC3, FDR)
- Confounds explain little overall (R²=0.036) — most variation is unit-idiosyncratic.
- **Synoptic parallels → more between-family disagreement** (β=+0.033, p_fdr=0.0043): harmonisation pressure.
- **Prologue distinctively stable** across branches (β=-0.075, p_fdr=0.002), robust to confounds.
- Section adds signal beyond confounds (Wald χ²=13.397, p=0.00385) — entirely Prologue-driven; ch21/Farewell not distinctive.

## Textual-stability map (complement of instability)
- Mean consensus (majority reading / extant) = 0.933; 6,338/10,947 units (58%) are near-unanimous anchors.
- Most stable chapters: [16, 20, 21, 15, 14]; least stable: [10, 8, 6, 19, 13].
- Family internal homogeneity: {'f1': 0.745, 'f13': 0.833, 'Byz': 0.631, 'Alexandrian': 0.667}.

## Robustness (do the findings survive resampling/perturbation?)
- **Overall robust: True.** Leave-one-family Spearman ≥ 0.929 (map not driven by any one family).
- Prologue-stable coefficient bootstrap CI (-0.1059, -0.0381) (robustly negative: True); Synoptic CI (0.0127, 0.0534) (robustly positive: True).
- Ch21 stays low under every family drop (True); its bootstrap CI overlaps the median, so it is 'not elevated', not 'uniquely most stable'.

## RQ4 — stylometry (function-word Burrows's Delta; hypothesis-generating only)
- Method validated: large-sample same-author Δ=0.72 vs different-author Δ=1.30 (separates authors).
- Size-matched test: **no John section exceeds the Gospel's own body-internal variability** (any seam? False). The naive 'Prologue distinct' is a sample-size artifact, not a stylistic seam. Authorship stays out of scope.

## What was refuted from the pre-rebuild project
- "Variant density = compositional age": the old metric counted intra-manuscript corrections, failed its own Pericope-Adulterae test, and is discarded.
- "Chapter 21 more unstable = later addition": with real collation + genealogy, ch21 is among the LEAST unstable chapters and not distinctive after controls.

## Scope / honesty
- This is a TRANSMISSION-history study. Manuscript data records scribal copying, not authorial composition; no composition-date or authorship claim is made.
- Münster CBGM is unavailable for John; the genealogy here is our own pre-genealogical coherence, validated against published family lists.