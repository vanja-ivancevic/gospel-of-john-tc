# Gospel of John: Computational Textual Criticism

A reproducible study of where the text of John shifted as scribes copied it, built on a real
cross-witness collation: the IGNTP/INTF *Editio Critica Maior* apparatus, 215 Greek witnesses
compared against the NA28 base text.

The whole pipeline runs from one command, every number traces back to the committed apparatus, and a
public dashboard lets anyone drill from a gospel-wide map down to the manuscripts behind a single word.

## What this is

This is a transmission-history study. It maps where the manuscripts agree on John's wording and where
they diverge, across more than a thousand years of hand copying. The evidence is copying behaviour, so
the project stays silent on who wrote John and when. Manuscript variation tells you how the text was
transmitted, and that is the question here.

## How it measures stability

A manuscript earns its weight through its pedigree. About 215 copies of John survive, but a typical
verse is attested by around 140, and roughly three-quarters of those are near-identical Byzantine
copies that descend from a shared ancestor and echo one testimony. Counting them all as independent
voices overstates the evidence by an order of magnitude.

So the headline metric weighs by family. Each manuscript family (f1, f13, Byzantine, Alexandrian, and
a residual "other") casts one plurality vote, and **stability** is the share of families that agree at
a verse. The plain head-count version is kept alongside for comparison, because the choice to treat the
Byzantine majority as one voice is the mainstream critical-text position and serious scholars contest
it. The two measures barely differ on average, yet they reshuffle which verses look firm.

Three more quantities round it out:

- **Instability** is `1 − stability`: how divided the tradition is at a verse.
- **Branch split** flags disagreement that runs *between* families, the deeper kind of variation.
- **Confidence** tracks how much early and independent evidence survives. A verse with a hundred late
  copies but only a handful of early or non-Byzantine witnesses gets flagged, because head-count alone
  hides thin attestation.

Each manuscript counts once per variation unit, so a codex's own corrector can never pull it onto two
sides of the same reading. Orthographic sub-variants count as agreement.

## What it finds

- **Known interpolations land in the right direction.** The Pericope Adulterae (John 7:53-8:11) is
  attested by 80 witnesses against ~140 for the surrounding text (block permutation p ≈ 1e-4). John 5:4
  appears only in much later copies (median ~1049 CE) and is missing from the earliest (~449 CE,
  p ≈ 1e-4). These serve as the validation gates the whole method has to clear.
- **Chapter 21, often read as a late appendix, is among the most stable chapters** in the gospel, which
  cuts against the idea that an appended ending should be textually turbulent.
- **The Farewell Discourse (John 14-17) reads as stylometrically distinct** from the narrative body in a
  size-matched permutation test. That is a register signal consistent with its genre, an extended
  monologue, and carries no claim about authorship.

Full numbers, with confound controls and robustness checks, land in
[`reports/REPORT.md`](reports/REPORT.md) (auto-generated).

## Data

| Layer | Source | Notes |
|---|---|---|
| Cross-witness apparatus (core) | ECM Greek apparatus of John, positive + negative, 21 TEI-XML chapters | `data/raw/ecm/`, CC&nbsp;BY(-NC) academic |
| Per-MS transcriptions | IGNTP/ITSEE TEI transcriptions of John | `data/raw/`, CC&nbsp;BY 4.0; witness links point here |
| Manuscript dates | INTF *Kurzgefasste Liste* (NTVMR) | `data/raw/ntvmr/`, century estimates |
| Stylometry controls | MorphGNT (Matthew, Luke, John, Romans, 1 John) | function-word Burrows's Delta |
| English orientation text | World English Bible | public domain; tracks the verse for orientation, with the Greek units carrying the variation |

## Run

```bash
uv sync --extra dev
uv run python -m john_tc.pipeline          # raw ECM -> every table, figure, and reports/REPORT.md
uv run python -m john_tc.pipeline --fast   # same, but with lighter bootstrap settings
uv run pytest                              # tests + ground-truth gates
```

Pipeline stages live under `src/john_tc/`:
`ingest → metrics (instability, families, dates, genealogy, weighted) → validate → analysis → report`.

```
config.yaml              # single source of constants (corpus, seeds, thresholds, validation targets)
src/john_tc/
  ingest/apparatus.py    # ECM TEI-XML -> DuckDB collation store (units / readings / attestation)
  metrics/               # instability, families, dates, genealogy, weighted, stability
  analysis/              # confound-controlled regression, stylometry
  validate/              # interpolation gates, genealogy validation, robustness
  site/export_data.py    # precomputed JSON for the dashboard
data/raw/ecm/            # source apparatus (committed)
data/derived/            # DuckDB store (gitignored; regenerable)
```

## Dashboard

A dependency-free static site in `site/` drills from a gospel-wide stability heatmap into individual
verses, each rendered as running Greek with the variation marked inline, then into the variation units,
the competing readings, and the manuscripts behind each (named, dated, and linked to their IGNTP/ITSEE
transcription). It also carries a most-contested-verses list, jump-to-verse search, a colour-blind-safe
heatmap with a weighed/counted toggle, and the validation gates. No backend; the pipeline precomputes
`site/data/*.json`.

```bash
uv run python -m john_tc.site.export_data   # regenerate site data
cd site && python3 -m http.server 8777      # open http://localhost:8777
```

See [`site/README.md`](site/README.md) for deploy notes.

## Reproducibility and validation

The pipeline is seeded and deterministic, so a clean rebuild produces byte-identical output. Findings
have to survive the interpolation gates, confound-controlled regression (HC3 robust errors, FDR over
the focal hypotheses), and robustness checks (leave-one-family-out, cluster bootstrap intervals). The
recovered families are checked against the published f1/f13 lists with silhouette and bootstrap scores,
which test the distance metric, and the report says so. Nulls and small effects are reported plainly.
