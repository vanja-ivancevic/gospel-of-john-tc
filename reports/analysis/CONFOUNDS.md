# RQ2 — confound-controlled regression of textual instability

Controls: coverage, verse length, lectionary use, **and number of families** (the between-family-split outcome mechanically rises with how many families are co-extant, so family count is a confound, not just raw coverage). OLS with HC3 robust SEs is the headline; a fractional quasi-binomial logit GLM is reported as a functional-form sensitivity check (the outcome is a bounded proportion).

## DV: between_family_split  (n=879 verses)

- R² full = 0.0357, R² confounds-only = 0.0262
- Section adds signal beyond confounds? **True** (Wald χ²=13.358, p=0.003923)
- VIF (collinearity): {'coverage_z': 2.77, 'verse_length_z': 1.02, 'n_lectionaries_z': 2.72, 'n_families_z': 1.12, 'synoptic': 1.05}

| predictor | coef (β) | p | p (FDR, within model) |
|--|--|--|--|
| C(section, Treatment('body'))[T.appendix] | -0.0132 | 0.5524 | 0.7366 |
| C(section, Treatment('body'))[T.farewell] | -0.0039 | 0.7055 | 0.8063 |
| C(section, Treatment('body'))[T.prologue] | -0.0750 | 0.0003 | 0.0023 |
| coverage_z | -0.0046 | 0.516 | 0.7366 |
| verse_length_z | -0.0024 | 0.5195 | 0.7366 |
| n_lectionaries_z | -0.0068 | 0.4277 | 0.7366 |
| n_families_z | +0.0003 | 0.9471 | 0.9471 |
| synoptic | +0.0326 | 0.0019 | 0.0075 |

GLM (fractional logit) sensitivity on focal terms: synoptic: β=+0.221, p=0.0037, C(section, Treatment('body'))[T.appendix]: β=-0.207, p=0.256, C(section, Treatment('body'))[T.farewell]: β=-0.028, p=0.73, C(section, Treatment('body'))[T.prologue]: β=-0.889, p=0.0101

## DV: family_instability  (n=879 verses)

- R² full = 0.0201, R² confounds-only = 0.0051
- Section adds signal beyond confounds? **True** (Wald χ²=11.901, p=0.007731)
- VIF (collinearity): {'coverage_z': 2.77, 'verse_length_z': 1.02, 'n_lectionaries_z': 2.72, 'n_families_z': 1.12, 'synoptic': 1.05}

| predictor | coef (β) | p | p (FDR, within model) |
|--|--|--|--|
| C(section, Treatment('body'))[T.appendix] | -0.0229 | 0.3164 | 0.7429 |
| C(section, Treatment('body'))[T.farewell] | +0.0058 | 0.5638 | 0.7429 |
| C(section, Treatment('body'))[T.prologue] | -0.0829 | 0.0017 | 0.0134 |
| coverage_z | +0.0039 | 0.5576 | 0.7429 |
| verse_length_z | +0.0017 | 0.65 | 0.7429 |
| n_lectionaries_z | -0.0018 | 0.7821 | 0.7821 |
| n_families_z | -0.0030 | 0.4303 | 0.7429 |
| synoptic | +0.0145 | 0.1329 | 0.5316 |

GLM (fractional logit) sensitivity on focal terms: synoptic: β=+0.083, p=0.232, C(section, Treatment('body'))[T.appendix]: β=-0.197, p=0.233, C(section, Treatment('body'))[T.farewell]: β=+0.029, p=0.689, C(section, Treatment('body'))[T.prologue]: β=-0.850, p=0.0026

## Focal hypotheses — FDR across both outcomes (the correct test family)

| outcome | term | p | p (FDR) | survives |
|--|--|--|--|--|
| between_family_split | synoptic | 0.001872 | 0.004992 | yes |
| between_family_split | C(section, Treatment('body'))[T.appendix] | 0.5524 | 0.6444 | no |
| between_family_split | C(section, Treatment('body'))[T.farewell] | 0.7055 | 0.7055 | no |
| between_family_split | C(section, Treatment('body'))[T.prologue] | 0.0002839 | 0.002272 | yes |
| family_instability | synoptic | 0.1329 | 0.2658 | no |
| family_instability | C(section, Treatment('body'))[T.appendix] | 0.3164 | 0.5063 | no |
| family_instability | C(section, Treatment('body'))[T.farewell] | 0.5638 | 0.6444 | no |
| family_instability | C(section, Treatment('body'))[T.prologue] | 0.001678 | 0.004992 | yes |
