"""Parse the IGNTP/INTF ECM Greek apparatus of John into a normalized collation store.

The ECM apparatus is REAL cross-witness collation against the NA28 base text:

    <app n="B04K1V1" from="2" to="10" type="main">
      <lem wit="basetext">εν αρχη ην ο λογος</lem>
      <rdg n="a" wit="01 02 03 ...">εν αρχη ην ο λογος</rdg>   # = lemma reading
      <rdg n="b" type="om" wit="884">om</rdg>                  # a divergent reading
      ...
    </app>

Each <rdg @wit> is a space-separated list of Gregory-Aland sigla (with hand/corrector
suffixes). This is the quantity the old project mismeasured: a genuine disagreement
*between manuscripts*, not firsthand-vs-corrector inside one codex.

Output: a DuckDB database with three tables — `units`, `readings`, `attestation` (long).
Run:  python -m john_tc.ingest.apparatus
"""
from __future__ import annotations

import copy
import re
from pathlib import Path

import duckdb
import pandas as pd
from lxml import etree

from john_tc.config import Config, load_config

NS = {"t": "http://www.tei-c.org/ns/1.0"}
_VERSE_RE = re.compile(r"B(\d+)K(\d+)V(\d+)")
_BASE_GA_RE = re.compile(r"^(P\d+|L\d+|\d+)")


def parse_verse_id(verse_id: str) -> tuple[str, int, int]:
    """'B04K1V1' -> ('B04', 1, 1)."""
    m = _VERSE_RE.match(verse_id or "")
    if not m:
        return ("", -1, -1)
    return (f"B{m.group(1)}", int(m.group(2)), int(m.group(3)))


def normalize_siglum(raw: str) -> tuple[str, str]:
    """Collapse a raw apparatus siglum to (base_ga, hand).

    '01'->('01','firsthand')  '01*'->('01','firsthand')  '01Cca'->('01','corrector')
    '01S1'->('01','corrector')  '050-1'->('050','instance')  'L252-S1W1D1a'->('L252','lection')
    """
    m = _BASE_GA_RE.match(raw)
    base = m.group(1) if m else raw
    suffix = raw[len(base):]
    if suffix == "" or suffix == "*" or suffix == "V":  # plain text / firsthand / videtur
        hand = "firsthand"
    elif "C" in suffix or suffix.startswith("S") or "corr" in suffix or suffix.startswith("Z"):
        hand = "corrector"
    elif raw.startswith("L"):
        hand = "lection"
    elif "-" in suffix:
        hand = "instance"
    else:
        hand = "other"
    return base, hand


def _reading_text(rdg: etree._Element) -> str:
    """Text of a <rdg>, excluding any nested <wit><idno> witness listing."""
    clone = copy.deepcopy(rdg)
    for w in clone.findall("t:wit", NS):
        clone.remove(w)
    return " ".join("".join(clone.itertext()).split())


def parse_apparatus_file(path: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """Parse one ECM chapter file -> (unit_rows, reading_rows, attestation_rows)."""
    tree = etree.parse(str(path))
    units: list[dict] = []
    readings: list[dict] = []
    attest: list[dict] = []

    for app in tree.iter("{%s}app" % NS["t"]):
        verse_id = app.get("n") or ""
        book, chapter, verse = parse_verse_id(verse_id)
        a_from = app.get("from")
        a_to = app.get("to")
        app_id = f"{verse_id}/{a_from or '_'}-{a_to or '_'}"
        lem = app.find("t:lem", NS)
        lemma_text = _reading_text(lem) if lem is not None else ""
        lemma_wit = lem.get("wit") if lem is not None else None

        rdgs = app.findall("t:rdg", NS)
        units.append(
            dict(
                app_id=app_id, book=book, chapter=chapter, verse=verse, verse_id=verse_id,
                app_from=int(a_from) if a_from else None,
                app_to=int(a_to) if a_to else None,
                app_type=app.get("type") or "main",
                lemma_text=lemma_text, lemma_wit=lemma_wit, n_readings=len(rdgs),
            )
        )
        for rdg in rdgs:
            rid = rdg.get("n") or ""
            rtext = _reading_text(rdg)
            rtype = rdg.get("type")  # None for substantive; 'om'/'lac'/'subreading' otherwise
            wit_raw = (rdg.get("wit") or "").split()
            is_lemma = bool(rtext) and rtext == lemma_text and rtype not in ("om", "lac")
            readings.append(
                dict(
                    app_id=app_id, reading_id=rid, reading_type=rtype, var_seq=rdg.get("varSeq"),
                    reading_text=rtext, is_lemma=is_lemma, n_wit_raw=len(wit_raw),
                )
            )
            for w in wit_raw:
                base, hand = normalize_siglum(w)
                attest.append(
                    dict(app_id=app_id, reading_id=rid, witness_raw=w, base_ga=base, hand=hand)
                )
    return units, readings, attest


def build_db(config: Config | None = None, polarity: str | None = None,
             db_path: Path | None = None) -> Path:
    """Parse every ECM chapter (chosen polarity) into a fresh DuckDB collation store."""
    cfg = config or load_config()
    polarity = polarity or cfg["corpus"]["density_polarity"]
    src_dir = cfg.path("ecm_positive" if polarity == "positive" else "ecm_negative")
    db_path = db_path or cfg.path("collation_db")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    files = sorted(src_dir.glob("John_chapter_*.xml"),
                   key=lambda p: int(re.search(r"_(\d+)\.xml", p.name).group(1)))
    if not files:
        raise FileNotFoundError(f"No ECM chapter files in {src_dir}")

    all_u, all_r, all_a = [], [], []
    for f in files:
        u, r, a = parse_apparatus_file(f)
        all_u += u
        all_r += r
        all_a += a

    units = pd.DataFrame(all_u)
    readings = pd.DataFrame(all_r)  # noqa: F841 — referenced by name in DuckDB SQL below
    attest = pd.DataFrame(all_a)  # noqa: F841 — referenced by name in DuckDB SQL below
    units["polarity"] = polarity

    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    con.execute("CREATE TABLE units AS SELECT * FROM units")
    con.execute("CREATE TABLE readings AS SELECT * FROM readings")
    con.execute("CREATE TABLE attestation AS SELECT * FROM attest")
    con.execute("CREATE INDEX idx_u_chap ON units(chapter, verse)")
    con.execute("CREATE INDEX idx_a_app ON attestation(app_id)")
    con.close()
    return db_path


def summary(db_path: Path | None = None) -> dict:
    """Quick integrity counts for the built collation store."""
    cfg = load_config()
    con = duckdb.connect(str(db_path or cfg.path("collation_db")), read_only=True)
    q = con.execute
    out = {
        "units_total": q("SELECT count(*) FROM units").fetchone()[0],
        "units_main": q("SELECT count(*) FROM units WHERE app_type='main'").fetchone()[0],
        "units_lac": q("SELECT count(*) FROM units WHERE app_type='lac'").fetchone()[0],
        "readings": q("SELECT count(*) FROM readings").fetchone()[0],
        "attestations": q("SELECT count(*) FROM attestation").fetchone()[0],
        "distinct_base_ga": q("SELECT count(DISTINCT base_ga) FROM attestation").fetchone()[0],
        "verses": q("SELECT count(DISTINCT verse_id) FROM units").fetchone()[0],
        "chapters": q("SELECT count(DISTINCT chapter) FROM units").fetchone()[0],
    }
    con.close()
    return out


def main() -> None:
    cfg = load_config()
    db = build_db(cfg)
    s = summary(db)
    print(f"Built collation store: {db}")
    for k, v in s.items():
        print(f"  {k:18s} {v}")


if __name__ == "__main__":
    main()
