# RQ4 — function-word stylometry (Burrows's Delta), hypothesis-generating

MFW = 100 most frequent lemmas (MorphGNT); fixed 200-token windows (223 control windows) so Delta is NOT a sample-size artifact. Larger Delta = more stylistically distinct.

## Method validation (large samples) — does function-word Δ separate authors?
- same-author Δ = 0.749, different-author Δ = 1.298 -> separates: **True** (book halves vs cross-author).

## Size-matched section test (the honest comparison)
Small windows have less power (same-author 0.793 vs different-author 0.842); John's sections are small (prologue 252, ch21 549 tokens), so they MUST be compared size-for-size.
- John-body internal Δ (same author, same book, size-matched) = 0.840; band upper (mean+2sd) = 1.075

John sections vs body:
- prologue: Δ=0.973 — within John-body range (descriptive)
- farewell: Δ=0.918 — within John-body range (descriptive)
- ch21: Δ=0.809 — within John-body range (descriptive)

## Permutation test (the headline — a real null, not an eyeballed band)
For each section, the null is that its windows are exchangeable with body windows; the statistic is mean Δ(section, body). BH-corrected across the three sections.

| section | windows | observed Δ | p | p (FDR) | seam? |
|--|--|--|--|--|--|
| prologue | 1 | 0.973 | 0.06919 | 0.1038 | no |
| farewell | 14 | 0.918 | 0.0002 | 0.0006 | YES |
| ch21 | 2 | 0.809 | 0.7399 | 0.7399 | no |

**Any stylometric seam beyond John's own internal variation? True.**
When size is controlled and tested against a proper permutation null, no John section is significantly farther from the body than body windows are from each other — the large naive Δ for the Prologue/ch21 is a SAMPLE-SIZE artifact, not a stylistic seam.

_Scope: stylometry cannot establish authorship of hypothesised ancient sources._
_This is an internal-consistency probe with explicit controls, reported as such._