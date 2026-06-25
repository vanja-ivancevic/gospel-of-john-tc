# CLAUDE.md — guide for AI/dev sessions

Computational textual criticism of the **Gospel of John**, rebuilt from the ground up in
June 2026. This file is the canonical orientation; read it first.

## What this project is (and is NOT)

A **transmission-history** study: where is John's text unstable across the manuscript
tradition, and what explains it. Built on **real cross-witness collation** (the IGNTP/INTF
ECM Greek apparatus).

It is **NOT** an authorship/composition-dating project. Manuscript variation records *scribal
copying*, not *authorial composition*. Do not (re)introduce claims like "variant density =
compositional age" — that was the discarded pre-2026 project's fatal error.

## Why the rebuild happened (one paragraph)

The old project's "14,013 variants" were intra-manuscript firsthand-vs-corrector readings
inside single codices (0 of 254 files used cross-witness `wit=`; the count correlated r=0.94
with corrector richness). Every "variant density" claim was an artifact and failed its own
Pericope-Adulterae test. The rebuild swaps in the ECM apparatus (a genuine 215-witness
collation vs NA28) and re-derives everything with witness-normalized metrics, a validated
manuscript-family genealogy, confound controls, significance testing, and hard validation gates.

## Commands

```bash
uv sync --extra dev
uv run python -m john_tc.pipeline          # raw ECM -> all tables/figures/reports/REPORT.md
uv run python -m john_tc.pipeline --fast   # skip slow bootstrap validation
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
| `metrics/stability.py` | textual-stability map (consensus, anchors, family homogeneity) |
| `metrics/phylogeny.py` | UPGMA tree (PNG) + NEXUS export for SplitsTree/NeighborNet |
| `analysis/confounds.py` | RQ2 confound-controlled regression (verse-level, HC3, FDR) |
| `analysis/stylometry.py` | RQ4 function-word Burrows's Delta with known-author controls (MorphGNT) |
| `validate/interpolations.py` | hard gate: Pericope Adulterae must register as omitted |
| `validate/genealogy.py` | gate: families real (silhouette/bootstrap/ARI/sensitivity) |
| `validate/robustness.py` | stress-test findings (bootstrap CI, leave-one-family, confound CI) |
| `viz/heatmap.py` | standalone self-contained HTML stability heatmap |
| `site/export_data.py` | export precomputed JSON for the static public dashboard (`site/`) |
| `report.py` | assembles `reports/REPORT.md` (every number traces to data) |
| `pipeline.py` | runs all stages in dependency order |

The public dashboard is a dependency-free static SPA in `site/` (overview → chapter → verse →
variation unit → readings → witnesses). `site/data/` is generated; see `site/README.md`.

## Conventions (keep these)

- **Config-driven.** No magic constants in code; put them in `config.yaml`.
- **DuckDB store is regenerable** (`data/derived/`, gitignored). Never commit it; never treat
  pickles as a system of record (the old project's mistake).
- **Provenance over assertion.** Family labels carry `family_source` (`iohannes_list` =
  published, `manual`, `computed`). Never silently mix asserted and computed.
- **Validation gates before claims.** A finding ships only if the gates pass (PA, 5:4, family
  recovery) and it survives confound controls + FDR. Report nulls and small R² honestly.
- **Determinism.** Everything seeded from `config.yaml`.

## Data sources (`data/raw/`)

- `ecm/{positive,negative}/` — IGNTP/INTF ECM Greek apparatus of John (CC BY[-NC]); the core.
- `ntvmr/liste.csv` — INTF Kurzgefasste Liste metadata (dates).
- `translations/web_john.json` — World English Bible (public domain); dashboard orientation text
  only (not aligned to the Greek variation).
- `igntp/john_transcriptions_index.json` — GA→IGNTP/ITSEE transcription deep-link index
  (dashboard witness links point here, not NTVMR, whose workspace can't be deep-linked).
- `IGNTP_greek_john_transcriptions/`, `Byzantine_john_transcriptions/`, `Family1_*`,
  `Latin_*`, `coptic_*` — per-MS transcriptions (kept; Byz bundle used as genealogy ground truth).

## Key documents

- `reports/REPORT.md` — auto-generated headline findings.
- `reports/genealogy/VALIDATION.md`, `reports/analysis/CONFOUNDS.md` — detailed results.
- `AUDIT_2026/` — audit, code audit, source dossier, rebuild blueprint, genealogy plan; kept
  locally but **gitignored** (excluded from the published repo).

## Legacy (pre-2026, do not extend)

The frozen old project lives on git branch `main` (commit `2147f9a`). Its artifacts —
`scripts/`, `results/`, `run_complete_analysis.py`, `data/processed/*.pkl`, `data/exports/`,
`data/reference/`, `John_xml_parsing/`, `manuscripts xml/`, `docs/`, `PROJECT_SUMMARY.md` — have
been **removed from this `rebuild` branch** (they remain on `main` for the record). Don't restore
them; the project is `src/john_tc/` + `config.yaml`.
