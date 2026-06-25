# RQ2 — confound-controlled regression of textual instability

## DV: between_family_split  (n=879 verses)

- R² full = 0.0357, R² confounds-only = 0.0262
- Section adds signal beyond confounds? **True** (Wald χ²=13.397, p=0.003853)

| predictor | coef (β) | p | p (FDR) |
|--|--|--|--|
| C(section, Treatment('body'))[T.appendix] | -0.0128 | 0.5476 | 0.6388 |
| C(section, Treatment('body'))[T.farewell] | -0.0038 | 0.712 | 0.712 |
| C(section, Treatment('body'))[T.prologue] | -0.0750 | 0.0003 | 0.002 |
| coverage_z | -0.0045 | 0.5034 | 0.6388 |
| verse_length_z | -0.0024 | 0.5242 | 0.6388 |
| n_lectionaries_z | -0.0069 | 0.4165 | 0.6388 |
| synoptic | +0.0328 | 0.0012 | 0.0043 |

## DV: family_instability  (n=879 verses)

- R² full = 0.0194, R² confounds-only = 0.0042
- Section adds signal beyond confounds? **True** (Wald χ²=12.122, p=0.006975)

| predictor | coef (β) | p | p (FDR) |
|--|--|--|--|
| C(section, Treatment('body'))[T.appendix] | -0.0273 | 0.2191 | 0.5112 |
| C(section, Treatment('body'))[T.farewell] | +0.0042 | 0.6703 | 0.814 |
| C(section, Treatment('body'))[T.prologue] | -0.0829 | 0.0016 | 0.0114 |
| coverage_z | +0.0025 | 0.6932 | 0.814 |
| verse_length_z | +0.0014 | 0.6977 | 0.814 |
| n_lectionaries_z | -0.0012 | 0.8526 | 0.8526 |
| synoptic | +0.0124 | 0.1795 | 0.5112 |
