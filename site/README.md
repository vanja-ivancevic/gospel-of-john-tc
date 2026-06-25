# Unstable John — public dashboard

A dependency-free static site for drilling into the textual instability of the Gospel of John.
No backend: the pipeline precomputes everything into `site/data/*.json`, and the browser reads it.

## Structure

```
site/
  index.html      shell + nav + jump-to-verse search + favicon
  app.js          hash-router SPA: overview → chapter → verse → variation unit → readings → witnesses
  style.css
  data/           generated JSON (regenerate with the pipeline)
    summary.json    gospel stats, per-chapter metrics, validation gates, families
    verses.json     per-verse metric index (drives the heatmap + nav)
    families.json   families + per-witness family/date/name/NTVMR link
    chapters/N.json per-verse drill-down: running Greek text + inline slots → variation
                    units → readings → family breakdown + witness sigla; WEB English orientation
  assets/         witness genealogy tree (PNG) + NEXUS export (NeighborNet in SplitsTree)
```

## Features

- **Inline apparatus.** A verse renders its running Greek text with variation points marked: coloured
  words carry substantive variation, fainter ones are spelling-only, a `‸` caret marks an insertion
  point. Click a mark to jump to its readings. Toggle to hide spelling-only noise.
- **Hotspot leaderboard.** The overview ranks the most unstable verses (coverage-filtered).
- **Jump-to-verse search** (`3:16`) and a **witness filter** on the families page.
- **Identified witnesses.** Sigla deep-link to the manuscript's IGNTP/ITSEE transcription (same
  source as the data); majuscules show names.
- **Accessibility.** Colour-blind-safe (RdBu) heatmap with a low-coverage hatch, keyboard-navigable
  cells/rows/marks, per-route page titles.
- **Public-domain English** (World English Bible) for orientation — not aligned to the Greek variation.

## Run locally

```bash
# from repo root, regenerate the data (or run the full pipeline)
uv run python -m john_tc.site.export_data
# serve (a server is required — fetch() won't load from file://)
cd site && python3 -m http.server 8777
# open http://localhost:8777
```

## Deploy (any static host)

The site is plain static files — host `site/` as-is.

- **GitHub Pages**: move `site/` to `docs/` (Pages → Deploy from branch → `/docs`), or add a Pages
  Action that publishes the `site/` directory.
- **Cloudflare Pages / Netlify / Vercel**: build command none; output/publish directory `site`.

`data/` is committed so the site deploys without running the pipeline. Regenerate after any
analysis change with `uv run python -m john_tc.pipeline` (step 14b).

## Design notes

- Static + precomputed (unlike Münster's NTVMR, which needs a server for live CBGM queries —
  our analysis is fully precomputed, so a static site is the correct, durable choice).
- Drill-down mirrors the apparatus model (reading → witnesses) plus our genealogy-aware
  metrics (family-vote instability, between-family split) and validation gates.
