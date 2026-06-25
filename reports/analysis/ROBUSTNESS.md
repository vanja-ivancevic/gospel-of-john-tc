# Robustness / stability of the findings

Bootstrap B=80 (seeded). **Overall robust: True**

## 1. Bootstrap CIs on chapter instability
- Ch21 family-instability 95% CI upper bound below gospel median? **False** (the 'ch21 not elevated' claim is stable).

## 2. Leave-one-family-out (Spearman of chapter map vs full)
- drop Byz: ρ=0.929
- drop f1: ρ=0.991
- drop f13: ρ=0.982
- drop Alexandrian: ρ=0.982
- drop other: ρ=0.983
- min ρ = 0.929 (≥0.8 ⇒ not driven by any single family); ch21 stays low: True; ch19 stays high: True

## 3. Confound coefficients (bootstrap 95% CI)
- Prologue (between-family): CI (-0.1032, -0.0425) — robustly negative: True
- Synoptic parallels: CI (0.0111, 0.0528) — robustly positive: True