"""Dashboard data export — JSON shape the static site depends on."""
from __future__ import annotations

import json

import pytest

from john_tc.config import load_config


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    if not load_config().path("collation_db").exists():
        pytest.skip("collation store not built")
    from john_tc.site.export_data import export
    d = tmp_path_factory.mktemp("site_data")
    export(out_dir=d)
    return d


def _j(out, name):
    return json.loads((out / name).read_text(encoding="utf-8"))


def test_summary_has_meta_gates_chapters(out):
    s = _j(out, "summary.json")
    assert s["meta"]["n_witnesses"] == 215 and s["meta"]["n_verses"] == 879
    assert s["gates"]["pericope_adulterae"]["passed"] is True
    assert s["gates"]["john_5_4"]["passed"] is True
    assert len(s["chapters"]) == 21


def test_verses_index(out):
    v = _j(out, "verses.json")
    assert len(v) == 879
    j316 = next(x for x in v if x["verse_id"] == "B04K3V16")
    assert j316["ref"] == "John 3:16" and 0 <= j316["stability"] <= 1
    # family-vote ("weighed") metric + genealogical-confidence fields are exported per verse
    assert 0 <= j316["family_stability"] <= 1
    for k in ("n_families", "n_early", "eff_families", "low_conf"):
        assert k in j316
    assert isinstance(j316["low_conf"], bool)
    # confidence is genealogical, not a head-count: some well-covered verses are still flagged,
    # and the flag is not simply "few witnesses"
    assert any(x["low_conf"] for x in v) and any(not x["low_conf"] for x in v)


def test_chapter_detail_drilldown(out):
    d = _j(out, "chapters/3.json")
    v316 = next(x for x in d["verses"] if x["verse_id"] == "B04K3V16")
    assert v316["n_variation_units"] >= 1
    unit = v316["units"][0]
    assert "lemma" in unit and len(unit["readings"]) >= 2
    # witnesses are real manuscripts, never the editorial base text
    for r in unit["readings"]:
        assert "basetext" not in r["wits"]
        assert set(r["families"]).issubset({"f1", "f13", "Byz", "Alexandrian", "other"})


def test_export_is_deterministic(tmp_path_factory):
    """Two exports from the same store must be byte-identical (guards the family-tally overwrite
    bug + DuckDB unordered-aggregation nondeterminism)."""
    if not load_config().path("collation_db").exists():
        pytest.skip("collation store not built")
    from john_tc.site.export_data import export
    a = tmp_path_factory.mktemp("a")
    b = tmp_path_factory.mktemp("b")
    export(out_dir=a)
    export(out_dir=b)
    for name in ["summary.json", "verses.json", "families.json", "chapters/3.json", "chapters/8.json"]:
        assert (a / name).read_bytes() == (b / name).read_bytes(), f"{name} not deterministic"


def test_families_and_witnesses(out):
    f = _j(out, "families.json")
    fams = {x["family"] for x in f["families"]}
    assert {"f1", "f13", "Byz", "Alexandrian"}.issubset(fams)
    assert len(f["witnesses"]) > 150
    # witnesses link to their IGNTP transcription; recognised majuscules carry a name
    by_ga = {w["ga"]: w for w in f["witnesses"]}
    assert by_ga["03"]["name"].startswith("Vaticanus")
    assert by_ga["03"]["url"].endswith("NT_GRC_03_John.xml")
    assert "itseeweb.cal.bham.ac.uk" in by_ga["03"]["url"]
    # the editorial base text is not a manuscript -> no transcription link
    assert by_ga["basetext"]["url"] is None


def test_verse_running_text_and_inline_marks(out):
    d = _j(out, "chapters/3.json")
    v = next(x for x in d["verses"] if x["verse_id"] == "B04K3V16")
    # full running Greek text is present and contains the lemma of a known unit
    assert "ηγαπησεν" in v["text"]
    # slots tile the verse; at least one is a clickable variation point with an app id
    assert v["slots"] and any(s["var"] and s["app"] for s in v["slots"])
    # every variation slot's app id resolves to a unit card
    card_ids = {u["app_id"] for u in v["units"]}
    for s in v["slots"]:
        if s["var"] and s["app"] is not None:
            assert s["app"] in card_ids
    # public-domain English orientation text exported
    assert isinstance(v["english"], str) and "loved the world" in v["english"]


def test_orthographic_flag(out):
    d = _j(out, "chapters/3.json")
    v = next(x for x in d["verses"] if x["verse_id"] == "B04K3V16")
    assert all("orthographic" in u for u in v["units"])
