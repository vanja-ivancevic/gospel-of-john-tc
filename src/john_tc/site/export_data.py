"""Export precomputed analysis to static JSON for the public dashboard.

Writes to site/data/:
  summary.json          gospel stats, per-chapter metrics, families, validation gates
  verses.json           per-verse metric index (drives the heatmap + nav)
  families.json         families (size, homogeneity, source) + witness list (family, date, NTVMR)
  chapters/<n>.json     per-verse drill-down: running text -> variation units -> readings -> wits

The site is fully static (no backend), so these files ARE the database the browser queries.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

from john_tc.config import load_config

FAMILIES = ["f1", "f13", "Byz", "Alexandrian", "other"]

# Named witnesses (the ones a reader is likely to recognise); GA -> common name.
WITNESS_NAMES = {
    "P45": "Chester Beatty I", "P52": "Rylands fragment", "P66": "Bodmer II",
    "P75": "Bodmer XIV–XV", "P90": "Oxyrhynchus 3523",
    "01": "Sinaiticus (ℵ)", "02": "Alexandrinus (A)", "03": "Vaticanus (B)",
    "04": "Ephraemi Rescriptus (C)", "05": "Bezae (D)", "019": "Regius (L)",
    "022": "Petropolitanus Purpureus (N)", "032": "Washingtonianus (W)",
    "038": "Koridethi (Θ)", "044": "Athous Lavrensis (Ψ)",
    "0141": "Codex 0141", "0162": "Oxyrhynchus 847",
    "1": "Minuscule 1", "13": "Minuscule 13", "1582": "Minuscule 1582",
    "33": "Codex 33 (queen of the minuscules)", "565": "Minuscule 565",
    "579": "Minuscule 579", "700": "Minuscule 700", "892": "Minuscule 892",
}
def _igntp_index() -> tuple[str, set]:
    """Per-manuscript IGNTP/ITSEE transcription links (deep-link to the exact MS, renders via
    XSLT). Returns (url_template, available GA set). NTVMR's workspace can't be reliably
    deep-linked, so we point at the IGNTP transcriptions instead — the same source as our data."""
    p = load_config().root / "data/raw/igntp/john_transcriptions_index.json"
    if not p.exists():
        return "", set()
    d = json.loads(p.read_text(encoding="utf-8"))
    return d["url_template"], set(d["available"])


def _round(x, n=4):
    return round(float(x), n) if x is not None else None


def _english() -> dict:
    """Public-domain orientation translation (World English Bible), if vendored."""
    p = load_config().root / "data/raw/translations/web_john.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8")).get("verses", {})


def _verse_index(con) -> list[dict]:
    # Confidence is genealogical, not a head-count: "witnesses are weighed, not counted".
    #   coverage     = raw distinct manuscripts (shown, but redundant under the Byzantine mass)
    #   n_families   = distinct families extant (genealogical breadth, 0-5)
    #   eff_families = Simpson effective number of families, 1/Σ p_f² (independence-aware)
    #   n_early      = witnesses dated <= 500 CE (the text-critically weighty early evidence)
    rows = con.execute("""
        WITH att AS (
            SELECT DISTINCT u.verse_id, a.base_ga
            FROM units u JOIN readings r ON r.app_id=u.app_id
            JOIN attestation a ON a.app_id=r.app_id AND a.reading_id=r.reading_id
            WHERE u.app_type='main' AND r.reading_type IS DISTINCT FROM 'lac'
                  AND a.base_ga <> 'basetext'),
        fam AS (SELECT v.verse_id, coalesce(m.family,'other') AS family, count(*) AS n
                FROM att v LEFT JOIN witness_metadata m ON m.base_ga=v.base_ga GROUP BY 1,2),
        tot AS (SELECT verse_id, sum(n) AS total, count(*) AS n_families FROM fam GROUP BY 1),
        simp AS (SELECT f.verse_id, sum((f.n::DOUBLE/t.total)*(f.n::DOUBLE/t.total)) AS sumsq
                 FROM fam f JOIN tot t USING(verse_id) GROUP BY 1),
        early AS (SELECT a.verse_id, count(*) AS n_early FROM att a
                  JOIN witness_metadata m ON m.base_ga=a.base_ga
                  WHERE m.date_mid IS NOT NULL AND m.date_mid<=500 GROUP BY 1),
        conf AS (SELECT t.verse_id, t.n_families, 1.0/simp.sumsq AS eff_families,
                        coalesce(e.n_early,0) AS n_early
                 FROM tot t JOIN simp USING(verse_id) LEFT JOIN early e USING(verse_id))
        SELECT mv.verse_id, mv.chapter, mv.verse, mv.n_units,
               mv.instability, mv.extant_base_ms AS coverage,
               vs.stability, vs.family_stability, vs.anchor_frac, vs.tied_units,
               uf.family_instability, uf.between_family_split,
               conf.n_families, conf.eff_families, conf.n_early
        FROM metrics_verse mv
        LEFT JOIN metrics_verse_stability vs USING (verse_id)
        LEFT JOIN (SELECT verse_id, avg(family_instability) AS family_instability,
                          avg(CAST(between_family_split AS DOUBLE)) AS between_family_split
                   FROM metrics_unit_family GROUP BY verse_id) uf USING (verse_id)
        LEFT JOIN conf USING (verse_id)
        ORDER BY mv.chapter, mv.verse
    """).fetchall()
    cols = ["verse_id", "chapter", "verse", "n_units", "instability", "coverage",
            "stability", "family_stability", "anchor_frac", "tied_units",
            "family_instability", "between_family_split",
            "n_families", "eff_families", "n_early"]
    out = []
    for r in rows:
        d = dict(zip(cols, r))
        d["ref"] = f"John {d['chapter']}:{d['verse']}"
        for k in ("instability", "stability", "family_stability", "anchor_frac",
                  "family_instability", "between_family_split"):
            d[k] = _round(d[k])
        d["eff_families"] = _round(d["eff_families"], 2)
        d["tied_units"] = int(d["tied_units"]) if d["tied_units"] is not None else 0
        for k in ("n_families", "n_early"):
            d[k] = int(d[k]) if d[k] is not None else 0
        out.append(d)
    # Genealogical-confidence flag (config-driven): thin EARLY attestation or too few families.
    dash = load_config()["dashboard"]
    for d in out:
        d["low_conf"] = bool(d["n_early"] <= dash["low_confidence_max_early"]
                             or d["n_families"] < dash["low_confidence_min_families"])
    return out


def _chapter_detail(con, chapter: int, english: dict) -> dict:
    # 'basetext' is the editorial NA28 base, not a manuscript -> exclude from all witness counts.
    real_wit = "a.base_ga <> 'basetext'"
    # coalesce NULL family (witnesses with no metadata row, e.g. versions/lectionaries) into 'other'
    # IN SQL, so they share one group with real 'other' — otherwise two groups collapse to the same
    # python key and the count is overwritten in a row-order-dependent (nondeterministic) way.
    fam = con.execute(f"""
        SELECT r.app_id, r.reading_id, coalesce(m.family,'other') AS family,
               count(DISTINCT a.base_ga) AS n
        FROM units u JOIN readings r ON r.app_id=u.app_id
        JOIN attestation a ON a.app_id=r.app_id AND a.reading_id=r.reading_id
        LEFT JOIN witness_metadata m ON m.base_ga=a.base_ga
        WHERE u.chapter=? AND u.app_type='main' AND r.reading_type IS DISTINCT FROM 'lac'
              AND {real_wit}
        GROUP BY 1,2,3
    """, [chapter]).fetchall()
    fam_map: dict[tuple, dict] = {}
    for app_id, rid, family, n in fam:
        d = fam_map.setdefault((app_id, rid), {})
        d[family] = d.get(family, 0) + int(n)  # accumulate (never overwrite)
    wit = con.execute(f"""
        SELECT r.app_id, r.reading_id, list(DISTINCT a.base_ga) AS wits
        FROM units u JOIN readings r ON r.app_id=u.app_id
        JOIN attestation a ON a.app_id=r.app_id AND a.reading_id=r.reading_id
        WHERE u.chapter=? AND u.app_type='main' AND r.reading_type IS DISTINCT FROM 'lac'
              AND {real_wit}
        GROUP BY 1,2
    """, [chapter]).fetchall()
    wit_map = {(a, r): sorted(w) for a, r, w in wit}
    rdg = con.execute("""
        SELECT u.verse_id, u.verse, u.app_id, u.app_from, u.app_to, u.lemma_text,
               r.reading_id, r.reading_type, r.reading_text, r.is_lemma
        FROM units u JOIN readings r ON r.app_id=u.app_id
        WHERE u.chapter=? AND u.app_type='main' AND r.reading_type IS DISTINCT FROM 'lac'
        ORDER BY u.verse, u.app_from, r.reading_id
    """, [chapter]).fetchall()

    units: dict[str, dict] = {}
    for (vid, verse, app_id, a_from, a_to, lemma, rid, rtype, rtext, is_lem) in rdg:
        u = units.setdefault(app_id, dict(
            app_id=app_id, verse_id=vid, verse=verse, app_from=a_from, app_to=a_to,
            lemma=lemma, readings=[]))
        fams = fam_map.get((app_id, rid), {})
        wits = wit_map.get((app_id, rid), [])
        u["readings"].append(dict(
            id=rid, type=rtype, text=rtext, is_lemma=bool(is_lem), n_wit=len(wits),
            families={f: fams.get(f, 0) for f in FAMILIES if fams.get(f)}, wits=wits))

    # A GENUINE variation unit has >=2 readings with real manuscript support. The ECM also has
    # unanimous spans (lemma only) and whole-verse container units -> not "instability" per se.
    def has_variation(u):
        return len([r for r in u["readings"] if r["n_wit"] > 0]) >= 2

    def orth_only(u):  # supported divergences are all orthographic/sub-readings (spelling, not text)
        div = [r for r in u["readings"] if r["n_wit"] > 0 and not r["is_lemma"]]
        return bool(div) and all(r["type"] == "subreading" for r in div)

    def trim(u):  # drop unsupported readings (keep the lemma for context); annotate witness count
        u["readings"] = [r for r in u["readings"] if r["n_wit"] > 0 or r["is_lemma"]]
        u["n_variant_wit"] = sum(r["n_wit"] for r in u["readings"] if not r["is_lemma"])
        u["orthographic"] = orth_only(u)
        return u

    by_verse: dict[int, list] = {}
    for u in units.values():
        by_verse.setdefault(u["verse"], []).append(u)

    verses_out = []
    for verse_no in sorted(by_verse):
        ulist = sorted(by_verse[verse_no], key=lambda u: (u["app_from"] or 0, u["app_to"] or 0))

        def nests(outer, inner):  # inner strictly inside outer
            return (inner["app_from"] >= outer["app_from"] and inner["app_to"] <= outer["app_to"]
                    and (inner["app_from"], inner["app_to"]) != (outer["app_from"], outer["app_to"]))

        containers = [u for u in ulist if any(nests(u, o) for o in ulist if o is not u)]
        cset = {id(u) for u in containers}
        atomic = [u for u in ulist if id(u) not in cset]

        # running text = atomic lemma tokens in order (skip 'om' = an addition point in the base)
        text = " ".join(u["lemma"] for u in atomic if u["lemma"] and u["lemma"] != "om")
        # slots tile the verse: each is plain lemma text, or a clickable variation point
        slots, cards = [], []
        for u in atomic:
            var = has_variation(u)
            slots.append(dict(app=u["app_id"] if var else None, text=u["lemma"],
                              om=(u["lemma"] == "om"), var=var,
                              orth=(var and orth_only(u))))
            if var:
                cards.append(trim(u))
        # whole-verse variation (PA omission, 5:4 ...) shown as a banner, not an inline slot
        whole = [trim(u) for u in containers if has_variation(u)]

        vid = f"B04K{chapter}V{verse_no}"
        verses_out.append(dict(
            verse=verse_no, verse_id=vid, ref=f"John {chapter}:{verse_no}",
            text=text, english=english.get(vid), slots=slots,
            units=cards, whole_verse=whole,
            n_units_total=len(ulist),
            n_variation_units=len(cards) + len(whole)))
    return dict(chapter=chapter, verses=verses_out)


def _families(con) -> dict:
    from john_tc.metrics.stability import family_homogeneity
    sizes = dict(con.execute(
        "SELECT family, count(*) FROM witness_metadata GROUP BY 1").fetchall())
    src = dict(con.execute(
        "SELECT family, any_value(family_source) FROM witness_metadata GROUP BY 1").fetchall())
    homog = family_homogeneity()
    fams = [dict(family=f, n=int(sizes.get(f, 0)), source=src.get(f),
                 homogeneity=homog.get(f)) for f in FAMILIES if sizes.get(f)]
    wits = con.execute("""
        SELECT base_ga, family, date_early, date_late, date_mid
        FROM witness_metadata ORDER BY family, base_ga""").fetchall()
    tmpl, avail = _igntp_index()
    witnesses = []
    for g, fa, de, dl, dm in wits:
        url = tmpl.format(ga=g) if (tmpl and g in avail) else None
        witnesses.append(dict(ga=g, family=fa, date_early=de, date_late=dl, date_mid=dm,
                              name=WITNESS_NAMES.get(g), url=url))
    return dict(families=fams, witnesses=witnesses)


def _summary(con, verses: list[dict], fams: dict) -> dict:
    chapters = con.execute("""
        SELECT c.chapter, c.n_verses, c.n_units, c.instability, c.coverage_mean,
               cf.family_instability, cf.between_family_split
        FROM metrics_chapter c
        LEFT JOIN metrics_chapter_family cf USING (chapter)
        ORDER BY c.chapter""").fetchall()
    chap = [dict(chapter=r[0], n_verses=r[1], n_units=r[2], instability=_round(r[3]),
                 coverage=_round(r[4], 1), family_instability=_round(r[5]),
                 between_family_split=_round(r[6])) for r in chapters]
    # gospel stability per chapter (from verse index): both metrics
    import statistics as st
    def chap_mean(key):
        by = {}
        for v in verses:
            by.setdefault(v["chapter"], []).append(v.get(key))
        return {c: ([x for x in vs if x is not None]) for c, vs in by.items()}
    flat_by, fam_by = chap_mean("stability"), chap_mean("family_stability")
    for c in chap:
        fv = flat_by.get(c["chapter"], [])
        fa = fam_by.get(c["chapter"], [])
        c["stability"] = _round(st.mean(fv)) if fv else None
        c["family_stability"] = _round(st.mean(fa)) if fa else None
    meta = con.execute("""SELECT
        (SELECT count(*) FROM units WHERE app_type='main'),
        (SELECT count(*) FROM attestation),
        (SELECT count(DISTINCT base_ga) FROM attestation),
        (SELECT count(DISTINCT verse_id) FROM units)""").fetchone()
    # gospel-wide "weighed, not counted" headline: ~141 witnesses but ~N effective family-voices
    eff = [v["eff_families"] for v in verses if v.get("eff_families") is not None]
    dash = load_config()["dashboard"]
    return dict(
        meta=dict(n_units=meta[0], n_attestations=meta[1], n_witnesses=meta[2],
                  n_verses=meta[3], source="IGNTP/INTF ECM Greek apparatus of John (vs NA28)",
                  median_witnesses_per_verse=int(st.median(
                      [v["coverage"] for v in verses if v.get("coverage")])),
                  eff_families_median=_round(st.median(eff), 2) if eff else None,
                  confidence_rule=(f"flagged when a verse has ≤{dash['low_confidence_max_early']} early "
                                   f"(≤{dash['early_witness_max_date']} CE) witnesses, or fewer than "
                                   f"{dash['low_confidence_min_families']} families survive")),
        chapters=chap, families=fams["families"],
    )


def _gates() -> dict:
    """Validation-gate facts for the overview (recovered known phenomena)."""
    from john_tc.metrics.dates import five_four_date_signal
    from john_tc.validate.interpolations import run_gate

    g = run_gate(n_perm=2000)["pericope_adulterae"]
    f = five_four_date_signal()
    geneal = "unknown"
    vp = load_config().path("reports") / "genealogy" / "VALIDATION.md"
    if vp.exists():
        for line in vp.read_text(encoding="utf-8").splitlines():
            if "VERDICT" in line:
                geneal = line.replace("*", "").split(":")[-1].strip()
    return dict(
        pericope_adulterae=dict(passed=bool(g["passed"]), target=round(g["target_mean"]),
                                rest=round(g["rest_mean"]), p=g["p_value"]),
        john_5_4=dict(passed=bool(f.get("omitters_earlier")),
                      omit_date=round(f.get("median_omitter_date", 0)),
                      incl_date=round(f.get("median_includer_date", 0)), p=f.get("p_value")),
        genealogy=geneal,
    )


def export(out_dir: Path | None = None, db_path: Path | None = None) -> Path:
    cfg = load_config()
    out_dir = out_dir or cfg.root / "site" / "data"
    (out_dir / "chapters").mkdir(parents=True, exist_ok=True)
    english = _english()
    con = duckdb.connect(str(db_path or cfg.path("collation_db")), read_only=True)
    verses = _verse_index(con)
    fams = _families(con)
    summary = _summary(con, verses, fams)
    chapters = {c: _chapter_detail(con, c, english) for c in range(1, cfg["corpus"]["n_chapters"] + 1)}
    con.close()
    # gates open their own (read-write) connections -> only after the export con is closed
    summary["gates"] = _gates()
    summary["translation"] = ({"name": "World English Bible", "license": "Public Domain"}
                              if english else None)

    def dump(name, obj):
        (out_dir / name).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")),
                                    encoding="utf-8")

    dump("summary.json", summary)
    dump("verses.json", verses)
    dump("families.json", fams)
    for c, data in chapters.items():
        dump(f"chapters/{c}.json", data)

    # copy genealogy artefacts into the site assets (if built): tree PNG + NEXUS for SplitsTree
    import shutil
    assets = out_dir.parent / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for fn in ("john_witness_tree.png", "john_witnesses.nex"):
        src = cfg.path("reports") / "genealogy" / fn
        if src.exists():
            shutil.copy(src, assets / fn)
    return out_dir


def main() -> None:
    out = export()
    total = sum(f.stat().st_size for f in out.rglob("*.json"))
    print(f"Exported site data to {out} ({total/1e6:.1f} MB across "
          f"{len(list(out.rglob('*.json')))} files)")


if __name__ == "__main__":
    main()
