"use strict";
const FAMS = ["f1", "f13", "Byz", "Alexandrian", "other"];
const FAMCOLOR = { f1:"#d62728", f13:"#ff7f0e", Byz:"#7f7f7f", Alexandrian:"#1f77b4", other:"#2ca02c" };
const app = document.getElementById("app");
const crumb = document.getElementById("crumb");
const cache = {};

async function load(path) {
  if (!cache[path]) cache[path] = fetch("data/" + path).then(r => r.json());
  return cache[path];
}
const esc = s => (s ?? "").toString().replace(/[&<>"]/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;" }[c]));
const pct = x => (x == null ? "—" : (x * 100).toFixed(0) + "%");
const f3 = x => (x == null ? "—" : x.toFixed(3));
const setTitle = t => { document.title = (t ? t + " — " : "") + "Unstable John"; };

// red (fluid) -> blue (firm): a colour-blind-safe diverging ramp (ColorBrewer RdBu).
const RAMP = [[202,0,32],[244,165,130],[247,247,247],[146,197,222],[5,113,176]];
function heat(v, min, max) {
  const t = Math.max(0, Math.min(1, (v - min) / (max - min)));
  const x = t * (RAMP.length - 1), i = Math.floor(x), f = x - i;
  const a = RAMP[i], b = RAMP[Math.min(i + 1, RAMP.length - 1)];
  return `rgb(${a.map((v,k)=>Math.round(v+(b[k]-v)*f)).join(",")})`;
}
function percentile(arr, p) {
  const s = [...arr].sort((a,b)=>a-b); return s[Math.floor(p/100*(s.length-1))];
}

// ---- heatmap (width-autofit; switchable orientation, vertical default on mobile) ----
const MOBILE = window.matchMedia("(max-width:640px)");
let HM = null, hmOrient = MOBILE.matches ? "vert" : "horiz", hmUserSet = false;
function hmCell(d, c, v) {
  if (!d || d.stability == null) return `<div class="c"></div>`;
  const lc = d.coverage != null && d.coverage < HM.lowcov ? " lowcov" : "";
  return `<div class="c has${lc}" tabindex="0" role="link" data-go="verse/${d.verse_id}"
    aria-label="John ${c}:${v}, stability ${f3(d.stability)}${lc?", low coverage":""}"
    style="background:${heat(d.stability, HM.lo, HM.hi)}"></div>`;
}
function renderHeat() {
  const el = document.getElementById("heatmap"); if (!el || !HM) return;
  const vert = hmOrient === "vert", cols = vert ? 21 : HM.maxv;
  let g = `<div class="hm ${vert?"vert":"horiz"}" style="--cols:${cols}"><div class="hh corner"></div>`;
  if (vert) {
    for (let c = 1; c <= 21; c++)
      g += `<div class="hh" tabindex="0" role="link" data-go="chapter/${c}" aria-label="John chapter ${c}">${c}</div>`;
    for (let v = 1; v <= HM.maxv; v++) {
      g += `<div class="rl">${v%5===0?v:""}</div>`;
      for (let c = 1; c <= 21; c++) g += hmCell(HM.byCV[c+":"+v], c, v);
    }
  } else {
    for (let v = 1; v <= HM.maxv; v++) g += `<div class="hh">${v%5===0?v:""}</div>`;
    for (let c = 1; c <= 21; c++) {
      g += `<div class="rl" tabindex="0" role="link" data-go="chapter/${c}" aria-label="John chapter ${c}">${c}</div>`;
      for (let v = 1; v <= HM.maxv; v++) g += hmCell(HM.byCV[c+":"+v], c, v);
    }
  }
  el.innerHTML = g + `</div>`;
  const btn = document.getElementById("hmtoggle");
  if (btn) btn.textContent = vert ? "↔ Horizontal" : "↕ Vertical";
  const ax = document.getElementById("hmaxis");
  if (ax) ax.innerHTML = vert
    ? `<span>rows ↓ <b>verse</b></span><span>columns → <b>chapter 1–21</b></span>`
    : `<span>rows ↓ <b>chapter 1–21</b></span><span>columns → <b>verse</b></span>`;
}
MOBILE.addEventListener("change", e => {
  if (hmUserSet) return; hmOrient = e.matches ? "vert" : "horiz"; renderHeat();
});

// hover/focus tooltip for heatmap cells (compact metrics + link to the verse page)
let TIP = null, tipTimer = null;
function ensureTip() {
  if (TIP) return TIP;
  TIP = document.createElement("div"); TIP.className = "hmtip"; TIP.hidden = true;
  TIP.addEventListener("mouseenter", () => clearTimeout(tipTimer));
  TIP.addEventListener("mouseleave", hideTip);
  document.body.appendChild(TIP);
  return TIP;
}
function tipHTML(d) {
  const lc = d.coverage != null && d.coverage < HM.lowcov;
  const row = (l, v) => `<div class="t-row"><span>${l}</span><b>${v}</b></div>`;
  return `<div class="t-ref">${esc(d.ref)}</div>
    ${row("Stability", f3(d.stability))}
    ${row("Instability", f3(d.instability))}
    ${row("Branch split", pct(d.between_family_split))}
    ${row("Coverage", (d.coverage==null?"—":d.coverage+" MS") + (lc?` <i class="warn">low</i>`:""))}
    <a class="t-more" href="#/verse/${esc(d.verse_id)}">more info →</a>`;
}
function showTip(cell) {
  const id = (cell.dataset.go || "").split("/")[1], d = HM && HM.byId[id];
  if (!d) return;
  const t = ensureTip(); clearTimeout(tipTimer); t.innerHTML = tipHTML(d); t.hidden = false;
  const r = cell.getBoundingClientRect(), tw = t.offsetWidth, th = t.offsetHeight;
  let x = r.left + r.width/2 - tw/2, y = r.top - th - 8;
  if (y < 6) y = r.bottom + 8;
  t.style.left = Math.max(6, Math.min(x, window.innerWidth - tw - 6)) + "px";
  t.style.top = y + "px";
}
function hideTip() { tipTimer = setTimeout(() => { if (TIP) TIP.hidden = true; }, 200); }
document.addEventListener("mouseover", e => { const c = e.target.closest(".c.has"); if (c) showTip(c); });
document.addEventListener("mouseout", e => { if (e.target.closest(".c.has")) hideTip(); });
document.addEventListener("focusin", e => { const c = e.target.closest(".c.has"); if (c) showTip(c); });
document.addEventListener("focusout", e => { if (e.target.closest(".c.has")) hideTip(); });
window.addEventListener("scroll", () => { if (TIP) TIP.hidden = true; }, { passive: true });

// witness identity (name + NTVMR link), loaded once from families.json
let WIT = null;
async function witIndex() {
  if (!WIT) {
    WIT = {};
    (await load("families.json")).witnesses.forEach(w => { WIT[w.ga] = w; });
  }
  return WIT;
}
function witChip(ga) {
  const w = (WIT && WIT[ga]) || {};
  const label = w.name ? `${esc(ga)} · ${esc(w.name)}` : esc(ga);
  const fam = w.family ? ` <i style="background:${FAMCOLOR[w.family]||"#999"}"></i>` : "";
  return w.url
    ? `<a class="chip" href="${esc(w.url)}" target="_blank" rel="noopener" title="${esc(w.name||ga)} — open the IGNTP transcription">${label}${fam}</a>`
    : `<span class="chip">${label}${fam}</span>`;
}

// ---------------- Overview ----------------
async function overview() {
  setTitle("");
  const [sum, verses] = await Promise.all([load("summary.json"), load("verses.json")]);
  crumb.innerHTML = "";
  const m = sum.meta, g = sum.gates;
  const stat = (n, l) => `<div class="stat"><div class="n">${n}</div><div class="l">${l}</div></div>`;
  let h = `<h1>Where is the Gospel of John textually unstable?</h1>
    <p class="sub">Each cell below is a verse, coloured by how strongly the manuscript tradition
    agrees on its wording. Click any verse to read it with the actual variation marked inline —
    the competing readings and which manuscripts back each. Built on a real
    ${m.n_witnesses}-witness collation.</p>
    <div class="stats">
      ${stat(m.n_units.toLocaleString(), "variation units")}
      ${stat(m.n_attestations.toLocaleString(), "witness attestations")}
      ${stat(m.n_witnesses, "manuscripts")}
      ${stat(m.n_verses, "verses")}
    </div>`;

  if (g) h += `<p class="sub" style="margin-top:14px">Validation —
    Pericope Adulterae <span class="gate ${g.pericope_adulterae.passed?"pass":"fail"}">
    ${g.pericope_adulterae.passed?"recovered":"failed"}</span>
    (${g.pericope_adulterae.target} vs ${g.pericope_adulterae.rest} MS) ·
    John 5:4 <span class="gate ${g.john_5_4.passed?"pass":"fail"}">
    ${g.john_5_4.passed?"recovered":"failed"}</span>
    (omitters ${g.john_5_4.omit_date} vs includers ${g.john_5_4.incl_date} CE) ·
    genealogy <span class="gate ${/PASS/i.test(g.genealogy)?"pass":"fail"}">${esc(g.genealogy)}</span></p>`;

  // heatmap (rendered after innerHTML via renderHeat(); orientation is toggleable)
  const stab = verses.map(v => v.stability).filter(x => x != null);
  const covs = verses.map(v => v.coverage).filter(x => x != null);
  HM = { lo: percentile(stab, 2), hi: Math.max(...stab), lowcov: percentile(covs, 15),
         maxv: Math.max(...verses.map(v => v.verse)), byCV: {}, byId: {} };
  verses.forEach(v => { HM.byCV[v.chapter + ":" + v.verse] = v; HM.byId[v.verse_id] = v; });
  h += `<div class="hm-head"><h2>Stability heatmap</h2>
      <button id="hmtoggle" class="hm-toggle" data-hmtoggle
        aria-label="Toggle heatmap orientation"></button></div>
    <div class="legend"><span>fluid ≤ ${HM.lo.toFixed(2)}</span><div class="bar"></div>
      <span>${HM.hi.toFixed(2)} firm</span>
      <span class="lc"><i class="hatch"></i> low confidence: &lt; ${Math.round(HM.lowcov)} witnesses</span></div>
    <div class="hm-axis" id="hmaxis"></div>
    <div class="hm-wrap" id="heatmap"></div>`;

  // hotspot leaderboard — most unstable verses (excluding fragmentary, low-coverage ones)
  const covMin = percentile(covs, 25);
  const hot = verses.filter(v => v.instability != null && v.coverage != null && v.coverage >= covMin)
    .sort((a,b) => b.instability - a.instability).slice(0, 12);
  h += `<h2>Most unstable verses</h2>
    <p class="sub">Ranked by raw instability, restricted to verses with adequate witness coverage
    (≥ ${Math.round(covMin)} MS) so fragmentary passages don't dominate. Click to inspect.</p>
    <table><thead><tr><th>#</th><th>Verse</th><th class="num">Instability</th>
      <th class="num">Stability</th><th class="num">Branch split</th>
      <th class="num">Coverage</th></tr></thead><tbody>`;
  hot.forEach((v, i) => {
    h += `<tr class="clik" tabindex="0" role="link" data-go="verse/${v.verse_id}"><td>${i+1}</td>
      <td>${v.ref}</td><td class="num">${f3(v.instability)}</td>
      <td class="num">${f3(v.stability)}</td><td class="num">${pct(v.between_family_split)}</td>
      <td class="num">${v.coverage==null?"—":v.coverage.toFixed(0)}</td></tr>`;
  });
  h += `</tbody></table>`;

  // chapter table
  h += `<h2>By chapter</h2><table><thead><tr><th>Ch</th><th class="num">Verses</th>
    <th class="num" title="Mean consensus: share on the majority reading">Stability</th>
    <th class="num" title="Witness-normalized divergence (flat, one witness one vote)">Instability</th>
    <th class="num" title="One family = one vote">Family-vote</th>
    <th class="num" title="Share of units where the major families disagree">Branch split</th>
    <th class="num">Coverage</th></tr></thead><tbody>`;
  sum.chapters.forEach(c => {
    h += `<tr class="clik" tabindex="0" role="link" data-go="chapter/${c.chapter}"><td>${c.chapter}</td>
      <td class="num">${c.n_verses}</td><td class="num">${f3(c.stability)}</td>
      <td class="num">${f3(c.instability)}</td><td class="num">${f3(c.family_instability)}</td>
      <td class="num">${pct(c.between_family_split)}</td>
      <td class="num">${c.coverage==null?"—":c.coverage.toFixed(0)}</td></tr>`;
  });
  h += `</tbody></table>`;
  app.innerHTML = h;
  renderHeat();
}

// ---------------- Chapter ----------------
async function chapter(n) {
  setTitle(`John ${n}`);
  const verses = (await load("verses.json")).filter(v => v.chapter == n);
  crumb.innerHTML = `<a href="#/">Overview</a> › John ${n}`;
  let h = `<h1>John ${n}</h1><p class="sub">Click a verse to read it with the variation marked
    inline. <b>Stability</b> = share of witnesses on the majority reading; <b>instability</b> is its
    complement; <b>branch split</b> = the major families disagree (deeper variation).</p>
    <table><thead><tr><th>Verse</th><th class="num">Stability</th>
    <th class="num">Instability</th><th class="num">Family-vote</th>
    <th class="num">Coverage</th></tr></thead><tbody>`;
  verses.forEach(v => {
    h += `<tr class="clik" tabindex="0" role="link" data-go="verse/${v.verse_id}"><td>${v.ref}</td>
      <td class="num">${f3(v.stability)}</td><td class="num">${f3(v.instability)}</td>
      <td class="num">${f3(v.family_instability)}</td>
      <td class="num">${v.coverage==null?"—":v.coverage.toFixed(0)}</td></tr>`;
  });
  app.innerHTML = h + `</tbody></table>`;
}

// ---------------- Verse drill-down ----------------
function famBar(families) {
  const total = FAMS.reduce((s,f)=>s+(families[f]||0),0) || 1;
  let bar = `<div class="fbar" title="${FAMS.filter(f=>families[f]).map(f=>f+": "+families[f]).join(", ")}">`;
  FAMS.forEach(f => { if (families[f]) bar += `<span style="width:${100*families[f]/total}%;background:${FAMCOLOR[f]}"></span>`; });
  return bar + `</div>`;
}
function readingRow(r) {
  const badge = r.is_lemma ? ["lemma","NA28"] : r.type === "om" ? ["om","omit"]
    : r.type === "subreading" ? ["sub","spelling"] : ["var","variant"];
  const txt = r.text === "om" ? `<span class="grk om">(omits)</span>` : `<span class="grk">${esc(r.text)}</span>`;
  const wits = r.wits && r.wits.length
    ? `<details class="wits"><summary>${r.n_wit} witness${r.n_wit==1?"":"es"}</summary>
       <div class="chips">${r.wits.map(witChip).join("")}</div></details>` : "";
  return `<div class="rdg"><span class="badge ${badge[0]}">${badge[1]}</span>
    <div>${txt}${wits}</div><div class="nw">${r.n_wit}</div>${famBar(r.families)}</div>`;
}
function unitCard(u) {
  return `<div class="unit${u.orthographic?" orth":""}" id="u-${esc(u.app_id)}">
    <div class="uh">words ${u.app_from}–${u.app_to} · base text: <b>${esc(u.lemma==="om"?"(addition point)":u.lemma)}</b>
      · ${u.n_variant_wit} witnesses diverge${u.orthographic?` <span class="tag">spelling only</span>`:""}</div>
    ${u.readings.map(readingRow).join("")}</div>`;
}
async function verse(vid) {
  const m = vid.match(/B04K(\d+)V(\d+)/); const ch = +m[1];
  await witIndex();
  const [idx, detail] = await Promise.all([load("verses.json"), load("chapters/" + ch + ".json")]);
  const vi = idx.find(v => v.verse_id === vid) || {};
  const vd = detail.verses.find(v => v.verse_id === vid)
    || { units: [], whole_verse: [], slots: [], n_units_total: 0 };
  setTitle(vi.ref || vid);
  crumb.innerHTML = `<a href="#/">Overview</a> › <a href="#/chapter/${ch}">John ${ch}</a> › ${vi.ref || vid}`;
  const M = (l, v, t) => `<div class="m" title="${esc(t||"")}">${l}<br><b>${v}</b></div>`;
  let h = `<h1>${vi.ref || vid}</h1>`;

  // running text with inline variation marks
  if (vd.slots && vd.slots.length) {
    const words = vd.slots.map(s => {
      if (s.om) return s.var
        ? `<a class="vw add" tabindex="0" role="button" data-app="${esc(s.app)}" aria-label="addition point — some witnesses insert text" title="addition point — some witnesses insert text">‸</a>` : "";
      if (!s.var) return `<span class="w">${esc(s.text)}</span>`;
      return `<a class="vw${s.orth?" orth":""}" tabindex="0" role="button" data-app="${esc(s.app)}"
        aria-label="${s.orth?"spelling variant":"variation"}: ${esc(s.text)}"
        title="${s.orth?"spelling variant":"variation"} — click for readings">${esc(s.text)}</a>`;
    }).filter(Boolean).join(" ");
    h += `<div class="verse-text grk">${words}</div>`;
  }
  if (vd.english) h += `<blockquote class="eng">${esc(vd.english)}
    <cite>World English Bible (public domain) — orientation only; not aligned to the Greek variation</cite></blockquote>`;

  h += `<div class="metricrow">
      ${M("Stability", f3(vi.stability), "Share of witnesses on the majority reading")}
      ${M("Instability", f3(vi.instability), "Complement of stability (witness-normalized)")}
      ${M("Family-vote instability", f3(vi.family_instability), "One family = one vote")}
      ${M("Branch split", pct(vi.between_family_split), "Do the major families disagree?")}
      ${M("Coverage (MS)", vi.coverage==null?"—":vi.coverage.toFixed(0), "Manuscripts extant here")}
      ${M("Variation units", `${vd.n_variation_units||0} / ${vd.n_units_total||0}`, "Units with real variation / total")}
    </div>
    <div class="controls"><label><input type="checkbox" id="hideorth"> Hide spelling-only variation</label></div>
    <div class="fam-key">${FAMS.map(f=>`<span><i style="background:${FAMCOLOR[f]}"></i>${f}</span>`).join("")}</div>`;

  (vd.whole_verse || []).forEach(u => {
    h += `<div class="unit whole" id="u-${esc(u.app_id)}">
      <div class="uh">⚠ whole-verse variation — ${u.n_variant_wit} witnesses diverge across the entire verse</div>
      ${u.readings.map(readingRow).join("")}</div>`;
  });
  if (!vd.units.length && !(vd.whole_verse||[]).length)
    h += `<p class="note">The whole tradition agrees here — no substantive variation recorded.</p>`;
  vd.units.forEach(u => { h += unitCard(u); });
  app.innerHTML = h;

  const cb = document.getElementById("hideorth");
  if (cb) cb.addEventListener("change", () => app.classList.toggle("no-orth", cb.checked));
}

// ---------------- Families ----------------
async function families() {
  setTitle("Manuscripts & families");
  const d = await load("families.json");
  crumb.innerHTML = `<a href="#/">Overview</a> › Manuscripts & families`;
  let h = `<h1>Manuscript families</h1><p class="sub">Families recovered from our own collation
    (pre-genealogical coherence) and validated against the published IGNTP lists. Homogeneity =
    1 − mean within-family distance (higher = tighter).</p>
    <table><thead><tr><th>Family</th><th class="num">Members</th><th class="num">Homogeneity</th>
    <th>Source</th></tr></thead><tbody>`;
  d.families.forEach(f => {
    h += `<tr><td><i style="display:inline-block;width:10px;height:10px;border-radius:2px;
      background:${FAMCOLOR[f.family]||"#999"};margin-right:6px"></i>${f.family}</td>
      <td class="num">${f.n}</td><td class="num">${f.homogeneity==null?"—":f.homogeneity}</td>
      <td>${esc(f.source||"")}</td></tr>`;
  });
  h += `</tbody></table>
    <h2>Witness genealogy</h2>
    <p class="sub">UPGMA tree from coherence distances; leaf colour = family.
      <a href="assets/john_witnesses.nex" download>Download NEXUS</a> for NeighborNet in SplitsTree.</p>
    <img class="tree" src="assets/john_witness_tree.png" alt="witness genealogy tree"
      onerror="this.style.display='none'">
    <h2>Witnesses (${d.witnesses.length})</h2>
    <p class="sub">GA numbers link to the IGNTP/ITSEE transcription of that manuscript.</p>
    <input class="filter" id="wfilter" type="text" placeholder="Filter by GA number or name…"
      aria-label="Filter witnesses">
    <table id="wtable"><thead><tr><th>GA</th><th>Name</th><th>Family</th>
      <th class="num">Date (CE)</th></tr></thead><tbody>`;
  d.witnesses.forEach(w => {
    const date = w.date_mid == null ? "—" : (w.date_early === w.date_late ? w.date_mid
      : `${w.date_early}–${w.date_late}`);
    const ga = w.url ? `<a href="${esc(w.url)}" target="_blank" rel="noopener">${esc(w.ga)}</a>` : esc(w.ga);
    h += `<tr data-k="${esc((w.ga+" "+(w.name||"")).toLowerCase())}"><td>${ga}</td>
      <td>${esc(w.name||"")}</td><td><i style="display:inline-block;width:9px;height:9px;
      border-radius:2px;background:${FAMCOLOR[w.family]||"#999"};margin-right:5px"></i>${esc(w.family)}</td>
      <td class="num">${date}</td></tr>`;
  });
  app.innerHTML = h + `</tbody></table>`;
  const filt = document.getElementById("wfilter");
  filt.addEventListener("input", () => {
    const q = filt.value.trim().toLowerCase();
    document.querySelectorAll("#wtable tbody tr").forEach(tr => {
      tr.style.display = !q || tr.dataset.k.includes(q) ? "" : "none";
    });
  });
}

// ---------------- Verses index ----------------
async function verses() {
  setTitle("Verses");
  const vs = await load("verses.json");
  crumb.innerHTML = `<a href="#/">Overview</a> › Verses`;
  let h = `<h1>All verses</h1><p class="sub">Every verse in John with its stability. Filter by
    reference (“3:16”, or “3:” for the whole chapter) and click to open.</p>
    <input class="filter" id="vfilter" type="text" placeholder="Jump to a verse — e.g. 3:16"
      aria-label="Filter verses by reference">
    <table id="vtable"><thead><tr><th>Verse</th><th class="num">Stability</th>
      <th class="num">Instability</th><th class="num">Branch split</th>
      <th class="num">Coverage</th></tr></thead><tbody>`;
  vs.forEach(v => {
    h += `<tr class="clik" tabindex="0" role="link" data-go="verse/${v.verse_id}"
      data-k="${v.chapter}:${v.verse}"><td>${v.ref}</td>
      <td class="num">${f3(v.stability)}</td><td class="num">${f3(v.instability)}</td>
      <td class="num">${pct(v.between_family_split)}</td>
      <td class="num">${v.coverage==null?"—":v.coverage.toFixed(0)}</td></tr>`;
  });
  app.innerHTML = h + `</tbody></table>`;
  const f = document.getElementById("vfilter"); f.focus();
  f.addEventListener("input", () => {
    const q = f.value.trim().toLowerCase();
    document.querySelectorAll("#vtable tbody tr").forEach(tr => {
      tr.style.display = !q || tr.dataset.k.includes(q) ? "" : "none";
    });
  });
}

// ---------------- About ----------------
async function about() {
  setTitle("Method & scope");
  const sum = await load("summary.json");
  crumb.innerHTML = `<a href="#/">Overview</a> › Method`;
  app.innerHTML = `<h1>Method &amp; scope</h1>
    <div class="note"><b>This is a transmission-history study.</b> It maps where the text of John
    is unstable across the manuscript tradition. Manuscript variation records scribal <i>copying</i>,
    not authorial <i>composition</i> — so no authorship or dating-of-composition claims are made.</div>
    <h2>Data</h2><p>${esc(sum.meta.source)} — ${sum.meta.n_witnesses} Greek witnesses,
    ${sum.meta.n_units.toLocaleString()} substantive variation units,
    ${sum.meta.n_attestations.toLocaleString()} witness attestations. The NA28 text is the base;
    each reading lists the manuscripts that carry it. The English orientation text is the public-domain
    World English Bible and is <i>not</i> aligned to the Greek variation.</p>
    <h2>Reading a verse</h2><p>On a verse page the Greek runs across the top with variation points
    marked: <a class="vw" data-app="x">coloured words</a> carry substantive variation, fainter ones
    are spelling-only, and a <b>‸</b> caret marks a point where some witnesses insert text. Click any
    mark to jump to its readings and the manuscripts behind each.</p>
    <h2>Metrics</h2>
    <ul>
      <li><b>Stability / instability</b> — share of attesting witnesses on the majority vs divergent
        reading (they are complements).</li>
      <li><b>Family-vote instability</b> — one family = one vote, so the ~120 near-identical Byzantine
        copies count once, not 120.</li>
      <li><b>Branch split</b> — whether the major families disagree (deeper, branch-level variation).</li>
    </ul>
    <h2>Validation</h2><p>Known interpolations must register in the right direction: the Pericope
    Adulterae (omitted by ~half the witnesses) and John 5:4 (omitted by the earliest). The
    family genealogy is validated (silhouette, bootstrap, ARI) against the published IGNTP lists.
    All findings are stress-tested for robustness (leave-one-family-out, bootstrap CIs).</p>
    <p class="sub">Münster's CBGM is unavailable for John, so the genealogy here is computed
    from the collation itself.</p>`;
}

// ---------------- Router + interactions ----------------
function go(route) { location.hash = "#/" + route; }
window.go = go;

// delegated navigation (keyboard + mouse) for any [data-go] element
function fireGo(el) { if (el && el.dataset.go) go(el.dataset.go); }
document.addEventListener("click", e => {
  const tg = e.target.closest("[data-hmtoggle]");
  if (tg) { hmOrient = hmOrient === "vert" ? "horiz" : "vert"; hmUserSet = true; renderHeat(); return; }
  const nav = e.target.closest("[data-go]"); if (nav) { fireGo(nav); return; }
  const vw = e.target.closest(".vw[data-app]");
  if (vw) { e.preventDefault(); focusUnit(vw.dataset.app); }
});
document.addEventListener("keydown", e => {
  if (e.key !== "Enter" && e.key !== " ") return;
  const el = e.target.closest("[data-go], .vw[data-app]");
  if (!el) return;
  e.preventDefault();
  if (el.dataset.go) fireGo(el); else focusUnit(el.dataset.app);
});
function focusUnit(app_id) {
  const el = document.getElementById("u-" + app_id);
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash");
}

// jump-to-verse search
const jump = document.getElementById("jump");
if (jump) jump.addEventListener("submit", e => {
  e.preventDefault();
  const q = document.getElementById("jumpq").value.trim();
  const m = q.match(/^(\d{1,2})\s*[:.\s]\s*(\d{1,3})$/);
  if (m) return go(`verse/B04K${+m[1]}V${+m[2]}`);
  const c = q.match(/^(\d{1,2})$/);
  if (c && +c[1] >= 1 && +c[1] <= 21) return go(`chapter/${+c[1]}`);
});

function setActiveNav(key) {
  document.querySelectorAll("nav a[data-nav]").forEach(a =>
    a.classList.toggle("active", a.dataset.nav === key));
}
async function route() {
  if (TIP) TIP.hidden = true;
  const h = (location.hash || "#/").slice(2);
  try {
    if (h === "" || h === "/") { setActiveNav(""); return overview(); }
    if (h.startsWith("chapter/")) { setActiveNav(""); return chapter(+h.split("/")[1]); }
    if (h.startsWith("verse/")) { setActiveNav(""); return verse(h.split("/")[1]); }
    if (h === "verses") { setActiveNav("verses"); return verses(); }
    if (h === "families") { setActiveNav("families"); return families(); }
    if (h === "about") { setActiveNav("about"); return about(); }
    setActiveNav(""); overview();
  } catch (e) { app.innerHTML = `<p class="note">Could not load this view: ${esc(e.message)}</p>`; }
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", route);
route();
