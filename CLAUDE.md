# CLAUDE.md — guide for AI/dev sessions

Computational textual criticism of the **Gospel of John**. This file is the canonical
orientation; read it first.

## What this project is (and is NOT)

A **transmission-history** study: where is John's text unstable across the manuscript
tradition, and what explains it. Built on **real cross-witness collation** (the IGNTP/INTF
ECM Greek apparatus, 215 witnesses vs NA28).

It is **NOT** an authorship or composition-dating project. Manuscript variation records *scribal
copying*, not *authorial composition*. Do not introduce claims like "variant density =
compositional age"; that confuses transmission with composition and the data cannot support it.

## Commands

```bash
uv sync --extra dev
uv run python -m john_tc.pipeline          # raw ECM -> all tables/figures/reports/REPORT.md
uv run python -m john_tc.pipeline --fast   # lighter bootstrap settings
uv run pytest                              # tests + ground-truth gates
uv run ruff check src tests
```

## Architecture (`src/john_tc/`)

| Module | Role |
|---|---|
| `config.py` | loads `config.yaml` — the single source of constants/seeds/thresholds/paths |
| `ingest/apparatus.py` | ECM TEI-XML → DuckDB collation store (`units`, `readings`, `attestation`) |
| `metrics/instability.py` | witness-normalized instability + per-verse coverage |
| `metrics/families.py` | family labels (official lists + provenance flag) + family weights |
| `metrics/dates.py` | NTVMR Liste dates by docID; the John 5:4 early-omission test |
| `metrics/genealogy.py` | pre-genealogical coherence → clustering → family recovery |
| `metrics/weighted_instability.py` | family-vote + between-family-split metrics (RQ1) |
| `metrics/stability.py` | textual-stability map (family-vote + raw consensus, anchors, homogeneity) |
| `metrics/phylogeny.py` | UPGMA tree (PNG) + NEXUS export for SplitsTree/NeighborNet |
| `analysis/confounds.py` | RQ2 confound-controlled regression (verse-level, HC3, FDR) |
| `analysis/stylometry.py` | RQ4 function-word Burrows's Delta with known-author controls (MorphGNT) |
| `validate/interpolations.py` | hard gate: Pericope Adulterae must register as omitted |
| `validate/genealogy.py` | gate: families real (silhouette/bootstrap/sensitivity; ARI reported) |
| `validate/robustness.py` | stress-test findings (bootstrap CI, leave-one-family, confound CI) |
| `viz/heatmap.py` | standalone self-contained HTML stability heatmap |
| `site/export_data.py` | export precomputed JSON for the static public dashboard (`site/`) |
| `report.py` | assembles `reports/REPORT.md` (every number traces to data) |
| `pipeline.py` | runs all stages in dependency order |

The public dashboard is a dependency-free static SPA in `site/` (overview → chapter → verse →
variation unit → readings → witnesses). `site/data/` is generated; see `site/README.md`.

## Conventions (keep these)

- **Config-driven.** No magic constants in code; put them in `config.yaml`.
- **DuckDB store is regenerable** (`data/derived/`, gitignored). Never commit it, and never treat
  a pickle as a system of record.
- **Provenance over assertion.** Family labels carry `family_source` (`iohannes_list` =
  published, `manual`, `computed`). Never silently mix asserted and computed.
- **Validation gates before claims.** A finding ships only if the gates pass (PA, 5:4, family
  recovery) and it survives confound controls + FDR. Report nulls and small R² honestly.
- **Weigh, don't count.** The headline stability metric is family-vote (one family one vote); the
  raw head-count is kept beside it as a labelled secondary, never as the lead.
- **Determinism.** Everything seeded from `config.yaml`; a clean rebuild is byte-identical.

## Writing (public-facing text)

README, dashboard copy, and reports go through the `humanizer` and `stop-slop` skills. State claims
affirmatively (avoid the "not X, it's Y" cadence), drop em dashes and adverb crutches, vary sentence
length, and keep a neutral register for reference text.

## Data sources (`data/raw/`)

- `ecm/{positive,negative}/` — IGNTP/INTF ECM Greek apparatus of John (CC BY[-NC]); the core.
- `ntvmr/liste.csv` — INTF Kurzgefasste Liste metadata (dates).
- `translations/web_john.json` — World English Bible (public domain); dashboard orientation text
  that follows the verse, not aligned to the Greek variation.
- `igntp/john_transcriptions_index.json` — GA→IGNTP/ITSEE transcription deep-link index
  (dashboard witness links point here; NTVMR's workspace can't be deep-linked).
- `IGNTP_greek_john_transcriptions/`, `Byzantine_john_transcriptions/`, `Family1_*`,
  `Latin_*`, `coptic_*` — per-MS transcriptions (the Byzantine bundle is the genealogy ground truth).

## Key documents

- `reports/REPORT.md` — auto-generated headline findings.
- `reports/genealogy/VALIDATION.md`, `reports/analysis/CONFOUNDS.md` — detailed results.
- `AUDIT_2026/` — internal methodology audit and working notes; gitignored, excluded from the repo.
