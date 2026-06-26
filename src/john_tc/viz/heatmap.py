"""Self-contained HTML stability heatmap of John's verses (no external dependencies).

Rows = chapters (1-21), columns = verse number, cell colour = textual stability
(green = the whole tradition agrees; red = fluid). Hover for per-verse detail.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np

from john_tc.config import load_config

_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Gospel of John — verse stability heatmap</title>
<style>
  :root {{ --cell: 15px; --gap: 1px; }}
  body {{ font: 13px/1.5 -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px;
          color: #1a1a1a; background: #fff; }}
  h1 {{ font-size: 19px; margin: 0 0 2px; }}
  p.sub {{ color: #666; margin: 0 0 18px; max-width: 760px; }}
  .wrap {{ overflow-x: auto; }}
  .grid {{ display: grid; gap: var(--gap);
           grid-template-columns: 34px repeat({maxv}, var(--cell)); }}
  .hdr, .rowlbl {{ font-size: 10px; color: #888; text-align: center; }}
  .rowlbl {{ text-align: right; padding-right: 5px; line-height: var(--cell); }}
  .cell {{ width: var(--cell); height: var(--cell); border-radius: 2px; cursor: pointer; }}
  .cell.empty {{ background: transparent; cursor: default; }}
  .cell:hover {{ outline: 2px solid #000; outline-offset: -1px; }}
  #tip {{ position: fixed; pointer-events: none; background: #111; color: #fff;
          padding: 6px 9px; border-radius: 5px; font-size: 12px; opacity: 0;
          transition: opacity .08s; max-width: 240px; z-index: 10; }}
  .legend {{ display: flex; align-items: center; gap: 8px; margin: 16px 0 4px; }}
  .bar {{ width: 220px; height: 12px; border-radius: 3px;
          background: linear-gradient(90deg,#b2182b,#f4a582,#ffffbf,#a6d96a,#1a9850); }}
  .meta {{ color:#666; font-size:12px; margin-top:10px; }}
</style></head><body>
<h1>Gospel of John — verse stability across the manuscript tradition</h1>
<p class="sub">Each cell is one verse. Colour = <b>family-vote stability</b> (share of manuscript families on
the majority reading, averaged over the verse's variation units). Green = the whole tradition
agrees; red = the text is fluid. Built from the IGNTP/INTF ECM apparatus ({nwit} witnesses).</p>
<div class="legend"><span>fluid ≤ {smin:.2f}</span><div class="bar"></div><span>{smax:.2f} firm</span></div>
<div class="wrap"><div id="grid" class="grid"></div></div>
<p class="meta">{nverses} verses · mean consensus {smean:.3f} · hover a cell for detail.<br>
Colour floor = 2nd percentile ({smin:.2f}) for contrast; {nbelow} extreme-fluid verse(s) clamp
to deepest red (lowest: John {truemin_verse} = {truemin:.2f}).</p>
<div id="tip"></div>
<script>
const DATA = {data};            // {{ "c:v": [stability, anchorPct, nUnits] }}
const MAXV = {maxv}, SMIN = {smin}, SMAX = {smax};
const grid = document.getElementById('grid'), tip = document.getElementById('tip');
function color(s) {{
  const t = Math.max(0, Math.min(1, (s - SMIN) / (SMAX - SMIN)));
  const stops = [[178,24,43],[244,165,130],[255,255,191],[166,217,106],[26,152,80]];
  const x = t * (stops.length - 1), i = Math.floor(x), f = x - i;
  const a = stops[i], b = stops[Math.min(i + 1, stops.length - 1)];
  const c = a.map((v, k) => Math.round(v + (b[k] - v) * f));
  return `rgb(${{c[0]}},${{c[1]}},${{c[2]}})`;
}}
// header row
grid.appendChild(Object.assign(document.createElement('div'), {{className:'hdr'}}));
for (let v = 1; v <= MAXV; v++) {{
  const h = document.createElement('div'); h.className = 'hdr';
  if (v % 5 === 0) h.textContent = v; grid.appendChild(h);
}}
// chapter rows
for (let c = 1; c <= 21; c++) {{
  const lbl = document.createElement('div'); lbl.className = 'rowlbl'; lbl.textContent = c;
  grid.appendChild(lbl);
  for (let v = 1; v <= MAXV; v++) {{
    const cell = document.createElement('div');
    const d = DATA[c + ':' + v];
    if (!d) {{ cell.className = 'cell empty'; }}
    else {{
      cell.className = 'cell'; cell.style.background = color(d[0]);
      cell.onmousemove = (e) => {{
        tip.style.opacity = 1; tip.style.left = (e.clientX + 14) + 'px';
        tip.style.top = (e.clientY + 14) + 'px';
        tip.innerHTML = `<b>John ${{c}}:${{v}}</b><br>stability ${{d[0].toFixed(3)}}`
          + `<br>anchors ${{d[1]}}% · ${{d[2]}} units`;
      }};
      cell.onmouseleave = () => {{ tip.style.opacity = 0; }};
    }}
    grid.appendChild(cell);
  }}
}}
</script></body></html>
"""


def build_heatmap(path: Path | None = None, db_path: Path | None = None) -> Path:
    cfg = load_config()
    path = path or cfg.path("reports") / "stability_heatmap.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path or cfg.path("collation_db")), read_only=True)
    # family-vote stability ("weighed"): one family one vote, Byzantine mass counts once
    rows = con.execute("""SELECT chapter, verse, verse_id, family_stability, anchor_frac, n_units
                          FROM metrics_verse_stability ORDER BY chapter, verse""").fetchall()
    nwit = con.execute("SELECT count(DISTINCT base_ga) FROM attestation").fetchone()[0]
    con.close()

    data = {f"{c}:{v}": [round(s, 4), round(af * 100), int(n)]
            for c, v, _vid, s, af, n in rows}
    stabs = [r[3] for r in rows]
    # Floor the colour scale at a robust percentile so one extreme outlier (John 10:42 = 0.33)
    # doesn't flatten the whole gradient. Values below the floor clamp to deepest red in JS.
    smin = float(np.percentile(stabs, 2))
    smax = float(max(stabs))
    smean = float(np.mean(stabs))
    truemin_row = min(rows, key=lambda r: r[3])
    nbelow = sum(1 for x in stabs if x < smin)
    html = _TEMPLATE.format(
        data=json.dumps(data, separators=(",", ":")),
        maxv=max(r[1] for r in rows), smin=smin, smax=smax, smean=smean,
        nverses=len(rows), nwit=nwit, nbelow=nbelow,
        truemin=truemin_row[3], truemin_verse=f"{truemin_row[0]}:{truemin_row[1]}",
    )
    path.write_text(html, encoding="utf-8")
    return path


def main() -> None:
    print("Wrote", build_heatmap())


if __name__ == "__main__":
    main()
