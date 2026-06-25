# Gospel of John — Computational Textual Criticism (rebuild 2026)

A reproducible study of **where the text of John is unstable across the manuscript
tradition**, built on real cross-witness collation data (the IGNTP/INTF *Editio Critica
Maior* apparatus). Rebuilt from the ground up in June 2026 after an audit found the
previous version's core dataset measured the wrong thing.

> **What changed and why:** the pre-rebuild pipeline counted intra-manuscript corrector
> readings rather than cross-witness disagreement (detailed below). The frozen baseline is
> preserved on the `main` branch (commit `2147f9a`); this rebuild lives on `rebuild`.

## The correction in one paragraph

The old pipeline counted `<app>/<rdg>` elements inside individual manuscript files and
called the total "14,013 variants." But those elements encode **firsthand-vs-corrector
readings inside one codex**, not disagreement *between* manuscripts (0 of 254 files used
cross-witness `wit=` markup; the count was dominated by a few heavily-corrected codices,
`r=0.94` with corrector richness). Every "variant density" claim therefore measured
scribal correction activity, was irreproducible, and *failed its own validation test*: the
Pericope Adulterae (the textbook late interpolation) came out **less** anomalous than its
surroundings. This rebuild swaps in the ECM apparatus — a genuine 215-witness collation
against the NA28 base text — and re-derives everything with witness-normalized metrics,
significance testing, and a hard validation gate.

## Research questions (defensible scope)

- **RQ1 — Transmission instability.** Where does the tradition disagree most, normalized by
  the witnesses actually attesting each unit?
- **RQ2 — What explains it?** Confound-controlled regression (lectionary use, syntactic
  difficulty, Synoptic parallels, coverage) before any "this section is special" claim.
- **RQ3 — Presence/absence of large units.** Recover known interpolations in the *right
  direction* (validation gate).
- **RQ4 — Stylometry (re-scoped).** Genre/register only, validated on known controls;
  authorship of hypothesized ancient sources is explicitly **out of scope** — manuscript
  data records *copying*, not *composition*.

## Current results

- ✅ **Validation gate passes.** Pericope Adulterae (John 7:53–8:11) attested by **80 vs
  ~140** manuscripts elsewhere (Δ=−59.8, permutation p≈1e-4). Correct direction.
- ✅ **Old headline refuted.** With real collation, **Chapter 21 is among the *least*
  unstable chapters** (instability 0.169 vs gospel mean ~0.19) — not the elevated "later
  addition" signal the old project reported.

## Data foundation

| Layer | Source | Notes |
|---|---|---|
| Cross-witness apparatus (core) | ECM Greek apparatus of John, neg+pos, 21 TEI-XML chapters | `data/raw/ecm/`, CC BY(-NC) academic |
| Per-MS transcriptions (kept) | 254 IGNTP TEI files | `data/raw/IGNTP_greek_john_transcriptions/`, CC BY 4.0 |

## Layout

```
config.yaml              # single source of constants (corpus, seeds, thresholds, validation targets)
pyproject.toml           # pinned deps (uv)
src/john_tc/
  config.py              # config loader
  ingest/apparatus.py    # ECM TEI-XML -> DuckDB collation store (units/readings/attestation)
  metrics/instability.py # witness-normalized instability + coverage
  validate/interpolations.py  # the hard validation gate
tests/                   # parser tests + golden counts + validation gate
data/raw/ecm/            # source apparatus (committed)
data/derived/            # DuckDB store (gitignored; regenerable)
```

## Run

```bash
uv sync --extra dev
uv run python -m john_tc.pipeline          # raw ECM -> every table, figure, and reports/REPORT.md
uv run python -m john_tc.pipeline --fast   # same, but skip the slow bootstrap validation
uv run pytest                              # tests + ground-truth gates
```

Headline findings land in [`reports/REPORT.md`](reports/REPORT.md) (auto-generated; every number
traces to the committed ECM apparatus). Pipeline stages live under `src/john_tc/`:
`ingest → metrics (instability, families, dates, genealogy, weighted) → validate → analysis → report`.

## Public dashboard

A dependency-free static site (`site/`) lets anyone drill from a gospel-wide stability heatmap
down into individual verses — each shown as **running Greek text with the variation marked inline**
→ variation units → competing readings → the manuscripts (named, dated, each linking to its
IGNTP/ITSEE transcription) behind each. Plus a most-unstable-verses leaderboard, jump-to-verse search, a colour-blind-safe
heatmap, and a public-domain English orientation text. No backend; the pipeline precomputes
`site/data/*.json`.

```bash
uv run python -m john_tc.site.export_data   # regenerate site data
cd site && python3 -m http.server 8777      # open http://localhost:8777
```
See [`site/README.md`](site/README.md) for deploy notes (GitHub/Cloudflare Pages).

## Status

All rebuild phases complete: data foundation (real ECM collation), validation gates (Pericope
Adulterae + John 5:4), manuscript-family genealogy built from our own collation and **rigorously
validated** (silhouette, bootstrap, ARI, sensitivity), genealogy-aware instability (RQ1),
confound-controlled regression (RQ2), re-scoped stylometry with known-author controls (RQ4),
and a one-command reproducible pipeline + CI.
