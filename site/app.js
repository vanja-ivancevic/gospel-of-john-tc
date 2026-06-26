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


// ---- heatmap (width-autofit; orientation + metric toggles) ----
// Two stability metrics, the textual-criticism "weighed vs counted" distinction:
//   family = family-vote ("weighed", default headline)   flat = raw head-count agreement ("counted")
const MOBILE = window.matchMedia("(max-width:640px)");
const METRIC_KEY = { family: "family_stability", flat: "stability" };
let HM = null, hmOrient = MOBILE.matches ? "vert" : "horiz", hmUserSet = false, hmMetric = "family";
let CONF_RULE = "thin early or independent attestation";
const hmScale = () => HM.scales[hmMetric];
const hmVal = d => d[METRIC_KEY[hmMetric]];
function hmCell(d, c, v) {
  const val = d ? hmVal(d) : null;
  if (val == null) return `<div class="c"></div>`;
  const sc = hmScale(), lc = d.low_conf ? " lowcov" : "";
  return `<div class="c has${lc}" tabindex="0" role="link" data-go="verse/${d.verse_id}"
    aria-label="John ${c}:${v}, ${hmMetric==='family'?'family-vote ':''}stability ${f3(val)}${lc?', low confidence':''}"
    style="background:${heat(val, sc.lo, sc.hi)}"></div>`;
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
  const ob = document.getElementById("hmtoggle");
  if (ob) ob.textContent = vert ? "↔ Horizontal" : "↕ Vertical";
  const mb = document.getElementById("hmmetric");
  if (mb) mb.textContent = hmMetric === "family" ? "Showing: family-vote (weighed)" : "Showing: raw head-count (counted)";
  const sc = hmScale(), leg = document.getElementById("hmlegend");
  if (leg) leg.innerHTML =
    `<span>fluid ≤ ${sc.lo.toFixed(2)}</span><div class="bar"></div><span>${sc.hi.toFixed(2)} firm</span>
     <span class="lc"><i class="hatch"></i> low confidence — ${esc(CONF_RULE)}</span>`;
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
  const row = (l, v) => `<div class="t-row"><span>${l}</span><b>${v}</b></div>`;
  return `<div class="t-ref">${esc(d.ref)}${d.low_conf?` <i class="warn">low conf.</i>`:""}</div>
    ${row("Stability (family-vote)", f3(d.family_stability))}
    ${row("Stability (raw count)", f3(d.stability))}
    ${row("Branch split", pct(d.between_family_split))}
    ${row("Witnesses", (d.coverage==null?"—":d.coverage) + ` · ${d.n_early??"—"} early`)}
    <a class="t-more" href="#/verse/${esc(d.verse_id)}">click for more info →</a>`;
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
    <p class="sub">As scribes copied John by hand for centuries, its wording drifted. This maps where
    the surviving Greek manuscripts <b>agree</b> and where they <b>disagree</b> — built on a real
    ${m.n_witnesses}-witness collation. Click any verse to read it with the variation marked inline:
    the competing readings and the manuscripts behind each.</p>
    <div class="stats">
      ${stat(m.n_units.toLocaleString(), "variation units")}
      ${stat(m.n_attestations.toLocaleString(), "witness attestations")}
      ${stat(m.n_witnesses, "manuscripts")}
      ${stat(m.n_verses, "verses")}
    </div>
    <div class="note" style="margin:6px 0 14px">Textual critics say witnesses are <b>weighed, not
      counted</b>: ~${m.n_witnesses} manuscripts survive, but ~${m.median_witnesses_per_verse} attest a
      typical verse and most are near-identical Byzantine copies — effectively only
      <b>~${m.eff_families_median} independent family-voices</b>. So the headline metric weighs by
      family; the raw head-count is shown alongside (toggle on the map). <a href="#/about">Full method →</a></div>
    <div class="defs">
      <div><span class="sw firm"></span><b>Stability (family-vote)</b> — the share of manuscript
        <i>families</i> that agree on the wording (one family = one vote, so the Byzantine mass counts
        once). <b>1.00</b> = all families agree. The dashboard default.</div>
      <div><span class="sw fluid"></span><b>Instability</b> — the flip side (1 − stability): how much
        the tradition disagrees. Higher = more contested.</div>
      <div><b>Raw agreement</b> — the same idea but counting every witness equally (Byzantine-heavy).
        Shown for comparison via the map's metric toggle.</div>
      <div><b>Branch split</b> — whether disagreement runs <i>between</i> families (deep variation).</div>
      <div><b>Confidence</b> — driven by <i>early/independent</i> depth, not head-count: a verse with
        100 late copies but few early or non-Byzantine witnesses is flagged low-confidence.</div>
    </div>`;

  if (g) h += `<div class="trust"><b>Does the method actually work?</b> Three checks against textbook
    cases — known scribal phenomena it must recover in the right direction:
    <ul>
      <li><b>Pericope Adulterae</b> (the woman caught in adultery, John 7:53–8:11) — the famous passage
        absent from the oldest manuscripts. Present here in only <b>${g.pericope_adulterae.target}</b>
        witnesses vs <b>${g.pericope_adulterae.rest}</b> for the surrounding text, so it's correctly
        flagged as a later insertion. <span class="gate ${g.pericope_adulterae.passed?"pass":"fail"}">${g.pericope_adulterae.passed?"recovered":"missed"}</span></li>
      <li><b>John 5:4</b> (the angel stirring the pool) — a known later addition. Here it shows up only
        in much later copies (median <b>${g.john_5_4.incl_date} CE</b>) and is missing from the earliest
        (median <b>${g.john_5_4.omit_date} CE</b>). <span class="gate ${g.john_5_4.passed?"pass":"fail"}">${g.john_5_4.passed?"recovered":"missed"}</span></li>
      <li><b>Manuscript families</b> — the family groupings recovered from the data match the published
        scholarly families. <span class="gate ${/PASS/i.test(g.genealogy)?"pass":"fail"}">${/PASS/i.test(g.genealogy)?"validated":esc(g.genealogy)}</span></li>
    </ul></div>`;

  // heatmap (rendered after innerHTML via renderHeat(); orientation is toggleable)
  const fam = verses.map(v => v.family_stability).filter(x => x != null);
  const flat = verses.map(v => v.stability).filter(x => x != null);
  CONF_RULE = (sum.meta && sum.meta.confidence_rule) || "thin early/independent attestation";
  HM = { scales: { family: { lo: percentile(fam, 2), hi: Math.max(...fam) },
                   flat: { lo: percentile(flat, 2), hi: Math.max(...flat) } },
         maxv: Math.max(...verses.map(v => v.verse)), byCV: {}, byId: {} };
  verses.forEach(v => { HM.byCV[v.chapter + ":" + v.verse] = v; HM.byId[v.verse_id] = v; });
  h += `<div class="hm-head"><h2>Stability heatmap</h2><div class="hm-btns">
      <button id="hmmetric" class="hm-toggle" data-hmmetric
        aria-label="Toggle weighed vs counted metric"></button>
      <button id="hmtoggle" class="hm-toggle" data-hmtoggle
        aria-label="Toggle heatmap orientation"></button></div></div>
    <div class="legend" id="hmlegend"></div>
    <div class="hm-axis" id="hmaxis"></div>
    <div class="hm-wrap" id="heatmap"></div>`;

  // hotspot leaderboard — most contested verses by family-vote, excluding low-confidence verses
  const hot = verses.filter(v => v.family_stability != null && !v.low_conf)
    .sort((a,b) => a.family_stability - b.family_stability).slice(0, 12);
  h += `<h2>Most contested verses</h2>
    <p class="sub">Ranked by family-vote instability (how much the manuscript families disagree),
    excluding low-confidence verses. Click to inspect the actual variation.</p>
    <table><thead><tr><th>#</th><th>Verse</th>
      <th class="num" title="One family = one vote (headline)">Stability (family)</th>
      <th class="num" title="Every witness counted equally">Stability (raw)</th>
      <th class="num">Branch split</th><th class="num">Witnesses</th></tr></thead><tbody>`;
  hot.forEach((v, i) => {
    h += `<tr class="clik" tabindex="0" role="link" data-go="verse/${v.verse_id}"><td>${i+1}</td>
      <td>${v.ref}</td><td class="num">${f3(v.family_stability)}</td>
      <td class="num">${f3(v.stability)}</td><td class="num">${pct(v.between_family_split)}</td>
      <td class="num">${v.coverage==null?"—":v.coverage.toFixed(0)}</td></tr>`;
  });
  h += `</tbody></table>`;

  // chapter table — family-vote headline, raw alongside
  h += `<h2>By chapter</h2><table><thead><tr><th>Ch</th><th class="num">Verses</th>
    <th class="num" title="Family-vote stability: one family one vote (headline)">Stability (family)</th>
    <th class="num" title="Raw head-count agreement, every witness equal">Stability (raw)</th>
    <th class="num" title="Share of units where the major families disagree">Branch split</th>
    <th class="num">Coverage</th></tr></thead><tbody>`;
  sum.chapters.forEach(c => {
    h += `<tr class="clik" tabindex="0" role="link" data-go="chapter/${c.chapter}"><td>${c.chapter}</td>
      <td class="num">${c.n_verses}</td><td class="num">${f3(c.family_stability)}</td>
      <td class="num">${f3(c.stability)}</td>
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
    inline. <b>Stability (family)</b> = share of manuscript families agreeing (one family one vote);
    <b>(raw)</b> counts every witness equally; <b>branch split</b> = the families disagree.
    † marks low-confidence verses (thin early/independent attestation).</p>
    <table><thead><tr><th>Verse</th><th class="num">Stability (family)</th>
    <th class="num">Stability (raw)</th><th class="num">Branch split</th>
    <th class="num">Coverage</th></tr></thead><tbody>`;
  verses.forEach(v => {
    h += `<tr class="clik" tabindex="0" role="link" data-go="verse/${v.verse_id}">
      <td>${v.ref}${v.low_conf?` <span class="lowmark" title="low confidence">†</span>`:""}</td>
      <td class="num">${f3(v.family_stability)}</td><td class="num">${f3(v.stability)}</td>
      <td class="num">${pct(v.between_family_split)}</td>
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
      ${M("Stability (family-vote)", f3(vi.family_stability), "Share of manuscript families agreeing — one family one vote (headline, 'weighed')")}
      ${M("Stability (raw count)", f3(vi.stability), "Share of all witnesses on the majority reading ('counted')")}
      ${M("Branch split", pct(vi.between_family_split), "Do the major families disagree with each other?")}
      ${M("Coverage", vi.coverage==null?"—":vi.coverage.toFixed(0), "Manuscripts extant here (raw head-count)")}
      ${M("Early witnesses", vi.n_early==null?"—":vi.n_early, "Witnesses dated ≤500 CE — the weighty early evidence")}
      ${M("Families", vi.n_families==null?"—":`${vi.n_families} (eff. ${vi.eff_families??"—"})`, "Distinct families present; effective independent count (Simpson)")}
      ${M("Variation units", `${vd.n_variation_units||0} / ${vd.n_units_total||0}`, "Units with real variation / total")}
    </div>
    ${vi.low_conf?`<div class="note warn-note">⚠ <b>Low confidence:</b> ${esc(CONF_RULE)} — read these
       numbers cautiously; the early/independent evidence here is thin.</div>`:""}
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
    <table id="vtable"><thead><tr><th>Verse</th><th class="num">Stability (family)</th>
      <th class="num">Stability (raw)</th><th class="num">Branch split</th>
      <th class="num">Coverage</th></tr></thead><tbody>`;
  vs.forEach(v => {
    h += `<tr class="clik" tabindex="0" role="link" data-go="verse/${v.verse_id}"
      data-k="${v.chapter}:${v.verse}"><td>${v.ref}${v.low_conf?` <span class="lowmark" title="low confidence">†</span>`:""}</td>
      <td class="num">${f3(v.family_stability)}</td><td class="num">${f3(v.stability)}</td>
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
  const m = sum.meta;
  app.innerHTML = `<h1>Method &amp; reasoning</h1>
    <div class="note"><b>This is a transmission-history study.</b> It maps where the text of John is
    unstable across the surviving manuscripts. Manuscript variation records scribal <i>copying</i>,
    not authorial <i>composition</i> — so no claims are made about who wrote John or when it was
    composed. Everything here is reproducible from the open data and code (linked below).</div>

    <h2>Data</h2>
    <p>${esc(m.source)} — <b>${m.n_witnesses}</b> Greek witnesses, <b>${m.n_units.toLocaleString()}</b>
    variation units, <b>${m.n_attestations.toLocaleString()}</b> witness attestations, collated against
    the NA28 base text. Each reading lists the manuscripts that carry it, with hand/corrector markup
    preserved. The English orientation text is the public-domain World English Bible and is <i>not</i>
    aligned to the Greek variation.</p>

    <h2>Why we weigh witnesses instead of counting them</h2>
    <p>A foundational rule of textual criticism is that <b>witnesses are weighed, not counted</b>
    (Westcott–Hort). Manuscripts that descend from a common ancestor repeat <i>one</i> testimony, so
    raw head-counts mislead. In John this is acute: ${m.n_witnesses} witnesses survive, but only about
    <b>${m.median_witnesses_per_verse}</b> attest a typical verse and roughly three-quarters of those
    are near-identical Byzantine copies — so a verse rests on effectively only
    <b>~${m.eff_families_median} independent family-voices</b> (Simpson's effective count), not ${m.median_witnesses_per_verse}.</p>
    <p>So the dashboard's <b>headline metric weighs by family</b> — each manuscript family casts one
    plurality vote, and stability is the share of families that agree. The naïve
    <b>raw head-count</b> agreement is kept alongside (the metric toggle on the heatmap) because it is
    the honest "counted" view. They differ: fixing the head-count's Byzantine bias <i>barely moves the
    average</i> but substantially <b>re-orders which verses look stable</b> — several verses that look
    firm by head-count are really just the Byzantine bloc agreeing with itself.</p>
    <div class="note">⚖ <b>An honest caveat.</b> Collapsing the Byzantine majority to one "voice" is the
    mainstream critical-text position, but it is a <i>position</i>, not a fact: Byzantine-priority
    scholars argue those manuscripts are many relatively independent witnesses. That is exactly why both
    views are shown — pick the lens you find defensible.</div>

    <h2>Metrics</h2>
    <ul>
      <li><b>Stability (family-vote)</b> — share of manuscript families agreeing on the wording, one
        family one vote (the Byzantine mass counts once). <b>Instability</b> is 1 − stability.</li>
      <li><b>Stability (raw)</b> — the same, but every witness counted equally. Byzantine-weighted.</li>
      <li><b>Branch split</b> — whether disagreement runs <i>between</i> families (deep, branch-level
        variation) rather than scattered within one family.</li>
      <li><b>Confidence</b> — based on <i>early and independent</i> depth, not head-count. A verse is
        flagged low-confidence when ${esc(m.confidence_rule)}. (Effective family count is ~${m.eff_families_median}
        for almost every verse, so it is reported gospel-wide rather than per verse.)</li>
    </ul>
    <p>One reading is counted per manuscript per unit (a codex's own <i>corrector</i> never makes it
    count as both agreeing and disagreeing — the intra-manuscript artifact that sank the project's
    earlier version), and purely orthographic sub-variants are treated as agreement.</p>

    <h2>Reading a verse</h2>
    <p>On a verse page the Greek runs across the top with variation points marked: coloured words carry
    substantive variation, fainter ones are spelling-only, and a <b>‸</b> caret marks where some
    witnesses insert text. Click any mark to jump to its readings and the manuscripts behind each;
    sigla link to the IGNTP/ITSEE transcription of that manuscript.</p>

    <h2>Manuscript families</h2>
    <p>Families (f1, f13, Byzantine, Alexandrian, and a residual "other") are recovered from our own
    collation by pre-genealogical coherence — the same starting point as Münster's CBGM — and the
    published f1/f13 lists are used as labels. <b>Hard families are a simplification:</b> modern method
    (CBGM) deliberately avoids rigid "text-types," so treat the buckets as a useful approximation of
    genealogical structure, not ground truth. Each witness carries a provenance flag (published list vs
    computed).</p>

    <h2>Validation &amp; honesty</h2>
    <p>The method must recover known scribal phenomena in the right direction: the <b>Pericope
    Adulterae</b> (absent from the oldest manuscripts) and <b>John 5:4</b> (carried only by later
    copies). The recovered families are checked against the published f1/f13 lists (silhouette,
    bootstrap, ARI) — which validates the <i>distance metric</i>, not the asserted labels — and findings
    are stress-tested (leave-one-family-out, bootstrap CIs). We report nulls and small effects plainly;
    a fuller audit of every methodological choice ships with the source.</p>

    <h2>Limitations</h2>
    <ul>
      <li>Greek continuous-text witnesses only (no versions/lectionary sub-analysis in the metrics).</li>
      <li>Manuscript dates are NTVMR century estimates; the date test is interval-sensitive.</li>
      <li>Families are an approximation (see above); "other" is a residual bucket.</li>
      <li>English is orientation only, not aligned to the Greek units.</li>
    </ul>
    <h2>Reproducibility</h2>
    <p>One command rebuilds every table, figure, report, and this dashboard from the raw apparatus;
    everything is seeded and deterministic (identical output across runs), and a published audit
    documents every methodological choice and its rationale — including where a check is a position
    rather than a fact (e.g. weighing Byzantine as one voice) and what the validation does and does
    not prove.</p>
    <p class="sub">Open source &amp; reproducible: the full pipeline, the methodology audit, and this
    site are at <a href="https://github.com/vanja-ivancevic/gospel-of-john-tc" target="_blank"
    rel="noopener">github.com/vanja-ivancevic/gospel-of-john-tc</a>. Münster's CBGM is gated for John,
    so the genealogy here is computed from the collation itself.</p>`;
}

// ---------------- Router + interactions ----------------
function go(route) { location.hash = "#/" + route; }
window.go = go;

// delegated navigation (keyboard + mouse) for any [data-go] element
function fireGo(el) { if (el && el.dataset.go) go(el.dataset.go); }
document.addEventListener("click", e => {
  const tg = e.target.closest("[data-hmtoggle]");
  if (tg) { hmOrient = hmOrient === "vert" ? "horiz" : "vert"; hmUserSet = true; renderHeat(); return; }
  const mt = e.target.closest("[data-hmmetric]");
  if (mt) { hmMetric = hmMetric === "family" ? "flat" : "family"; renderHeat(); return; }
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
