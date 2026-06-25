# RQ4 — function-word stylometry (Burrows's Delta), hypothesis-generating

MFW = 80 most frequent lemmas (MorphGNT); fixed 200-token windows (223 control windows) so Delta is NOT a sample-size artifact. Larger Delta = more stylistically distinct.

## Method validation (large samples) — does function-word Δ separate authors?
- same-author Δ = 0.721, different-author Δ = 1.303 -> separates: **True** (book halves vs cross-author).

## Size-matched section test (the honest comparison)
Small windows have less power (same-author 0.818 vs different-author 0.882); John's sections are small (prologue 252, ch21 549 tokens), so they MUST be compared size-for-size.
- John-body internal Δ (same author, same book, size-matched) = 0.887; band upper (mean+2sd) = 1.158

John sections vs body:
- prologue: Δ=1.050 — within John-body range
- farewell: Δ=0.989 — within John-body range
- ch21: Δ=0.826 — within John-body range

**Any stylometric seam beyond John's own internal variation? False.**
When size is controlled, no John section exceeds the Gospel's own body-internal variability — the large naive Δ for the Prologue/ch21 is a SAMPLE-SIZE artifact, not a stylistic seam.

_Scope: stylometry cannot establish authorship of hypothesised ancient sources._
_This is an internal-consistency probe with explicit controls, reported as such._