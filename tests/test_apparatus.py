"""Parser unit tests + golden integration counts for the ECM collation store."""
from __future__ import annotations

from pathlib import Path

import pytest

from john_tc.config import load_config
from john_tc.ingest.apparatus import normalize_siglum, parse_apparatus_file, parse_verse_id

FIXTURE = """<?xml version='1.0' encoding='utf-8'?>
<TEI xmlns="http://www.tei-c.org/ns/1.0"><div type="book"><div type="chapter">
<ab xml:id="B04K1V1-APP">
  <app n="B04K1V1" from="2" to="10" type="main">
    <lem wit="basetext">εν αρχη ην ο λογος</lem>
    <rdg n="a" wit="01 03 P66">εν αρχη ην ο λογος</rdg>
    <rdg n="b" type="om" wit="884 01Cca">om</rdg>
  </app>
  <app n="B04K1V1" type="lac">
    <lem wit="editorial">Whole verse</lem>
    <rdg type="lac" wit="P2 050-1">Def.</rdg>
  </app>
</ab></div></div></TEI>
"""


def test_parse_verse_id():
    assert parse_verse_id("B04K1V1") == ("B04", 1, 1)
    assert parse_verse_id("B04K21V25") == ("B04", 21, 25)
    assert parse_verse_id("garbage") == ("", -1, -1)


@pytest.mark.parametrize("raw,expected", [
    ("01", ("01", "firsthand")),
    ("01*", ("01", "firsthand")),
    ("01Cca", ("01", "corrector")),
    ("01S1", ("01", "corrector")),
    ("P66", ("P66", "firsthand")),
    ("884", ("884", "firsthand")),
    ("050-1", ("050", "instance")),
    ("L252-S1W1D1a", ("L252", "lection")),
])
def test_normalize_siglum(raw, expected):
    assert normalize_siglum(raw) == expected


def test_parse_apparatus_file(tmp_path: Path):
    f = tmp_path / "fixture.xml"
    f.write_text(FIXTURE, encoding="utf-8")
    units, readings, attest = parse_apparatus_file(f)

    assert len(units) == 2
    main = next(u for u in units if u["app_type"] == "main")
    assert main["verse_id"] == "B04K1V1" and main["chapter"] == 1
    assert main["app_from"] == 2 and main["app_to"] == 10
    assert main["lemma_text"] == "εν αρχη ην ο λογος"

    lemma_reading = next(r for r in readings if r["reading_id"] == "a")
    assert lemma_reading["is_lemma"] is True
    om_reading = next(r for r in readings if r["reading_id"] == "b")
    assert om_reading["reading_type"] == "om" and om_reading["is_lemma"] is False

    # base_ga collapses the corrector hand 01Cca -> 01
    bases = {(a["witness_raw"], a["base_ga"]) for a in attest}
    assert ("01Cca", "01") in bases
    assert ("050-1", "050") in bases


# ---- golden integration counts (require the built store) ----

@pytest.fixture(scope="module")
def db():
    p = load_config().path("collation_db")
    if not p.exists():
        pytest.skip("collation store not built; run `python -m john_tc.ingest.apparatus`")
    return p


def test_store_golden_counts(db):
    import duckdb
    con = duckdb.connect(str(db), read_only=True)
    n_main = con.execute("SELECT count(*) FROM units WHERE app_type='main'").fetchone()[0]
    n_base = con.execute("SELECT count(DISTINCT base_ga) FROM attestation").fetchone()[0]
    n_verses = con.execute("SELECT count(DISTINCT verse_id) FROM units").fetchone()[0]
    n_chap = con.execute("SELECT count(DISTINCT chapter) FROM units").fetchone()[0]
    con.close()
    assert n_main == 10947
    assert n_base == 215
    assert n_verses == 879
    assert n_chap == 21
