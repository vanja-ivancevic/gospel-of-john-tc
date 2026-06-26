# RQ2 — confound-controlled regression of textual instability

Controls: coverage, verse length, lectionary use, **and number of families** (the between-family-split outcome mechanically rises with how many families are co-extant, so family count is a confound, not just raw coverage). OLS with HC3 robust SEs is the headline; a fractional quasi-binomial logit GLM is reported as a functional-form sensitivity check (the outcome is a bounded proportion).

## DV: between_family_split  (n=879 verses)

- R² full = 0.0406, R² confounds-only = 0.0272
- Section adds signal beyond confounds? **True** (Wald χ²=22.005, p=6.509e-05)
- VIF (collinearity): {'coverage_z': 2.77, 'verse_length_z': 1.02, 'n_lectionaries_z': 2.72, 'n_families_z': 1.12, 'synoptic': 1.05}

| predictor | coef (β) | p | p (FDR, within model) |
|--|--|--|--|
| C(section, Treatment('body'))[T.appendix] | -0.0160 | 0.4539 | 0.7262 |
| C(section, Treatment('body'))[T.farewell] | -0.0055 | 0.6196 | 0.8107 |
| C(section, Treatment('body'))[T.prologue] | -0.0927 | 0 | 0 |
| coverage_z | -0.0081 | 0.3035 | 0.6069 |
| verse_length_z | -0.0072 | 0.069 | 0.184 |
| n_lectionaries_z | -0.0033 | 0.7094 | 0.8107 |
| n_families_z | -0.0004 | 0.9269 | 0.9269 |
| synoptic | +0.0319 | 0.0033 | 0.0134 |

GLM (fractional logit) sensitivity on focal terms: synoptic: β=+0.217, p=0.0056, C(section, Treatment('body'))[T.appendix]: β=-0.192, p=0.308, C(section, Treatment('body'))[T.farewell]: β=-0.023, p=0.783, C(section, Treatment('body'))[T.prologue]: β=-1.133, p=0.0036

## DV: family_instability  (n=879 verses)

- R² full = 0.0085, R² confounds-only = 0.0042
- Section adds signal beyond confounds? **False** (Wald χ²=4.212, p=0.2394)
- VIF (collinearity): {'coverage_z': 2.77, 'verse_length_z': 1.02, 'n_lectionaries_z': 2.72, 'n_families_z': 1.12, 'synoptic': 1.05}

| predictor | coef (β) | p | p (FDR, within model) |
|--|--|--|--|
| C(section, Treatment('body'))[T.appendix] | -0.0368 | 0.1628 | 0.564 |
| C(section, Treatment('body'))[T.farewell] | +0.0048 | 0.6657 | 0.8659 |
| C(section, Treatment('body'))[T.prologue] | -0.0293 | 0.2115 | 0.564 |
| coverage_z | -0.0027 | 0.7333 | 0.8659 |
| verse_length_z | +0.0072 | 0.0806 | 0.564 |
| n_lectionaries_z | +0.0013 | 0.8659 | 0.8659 |
| n_families_z | -0.0023 | 0.6005 | 0.8659 |
| synoptic | +0.0023 | 0.8314 | 0.8659 |

GLM (fractional logit) sensitivity on focal terms: synoptic: β=-0.006, p=0.93, C(section, Treatment('body'))[T.appendix]: β=-0.257, p=0.0911, C(section, Treatment('body'))[T.farewell]: β=+0.041, p=0.54, C(section, Treatment('body'))[T.prologue]: β=-0.219, p=0.281

## Focal hypotheses — FDR across both outcomes (the correct test family)

| outcome | term | p | p (FDR) | survives |
|--|--|--|--|--|
| between_family_split | synoptic | 0.003341 | 0.01337 | yes |
| between_family_split | C(section, Treatment('body'))[T.appendix] | 0.4539 | 0.7262 | no |
| between_family_split | C(section, Treatment('body'))[T.farewell] | 0.6196 | 0.7608 | no |
| between_family_split | C(section, Treatment('body'))[T.prologue] | 3.046e-06 | 2.436e-05 | yes |
| family_instability | synoptic | 0.8314 | 0.8314 | no |
| family_instability | C(section, Treatment('body'))[T.appendix] | 0.1628 | 0.423 | no |
| family_instability | C(section, Treatment('body'))[T.farewell] | 0.6657 | 0.7608 | no |
| family_instability | C(section, Treatment('body'))[T.prologue] | 0.2115 | 0.423 | no |
