"""RQ4 stylometry — method validity + the size-controlled (honest) section result."""
from __future__ import annotations

import pytest

from john_tc.config import load_config


def test_load_book_parses():
    from john_tc.analysis.stylometry import load_book
    jn = load_book("Jn")
    assert len(jn) > 14000
    assert {"chapter", "verse", "pos", "lemma"}.issubset(jn.columns)
    assert (jn.chapter == 1).any()


@pytest.fixture(scope="module")
def res():
    if not (load_config().root / "data/raw/morphgnt/64-Jn-morphgnt.txt").exists():
        pytest.skip("MorphGNT data not present")
    from john_tc.analysis.stylometry import run
    return run()


def test_method_separates_authors_at_scale(res):
    """Function-word Delta must clearly separate authors when samples are large (power)."""
    assert res["large_sample_separates"]
    assert res["large_sample"]["diff_author"] > res["large_sample"]["same_author"]


def test_no_section_seam_when_size_controlled(res):
    """The honest result: size-matched, no John section exceeds body-internal variability."""
    assert res["any_section_seam"] is False
    for v in res["sections_vs_body"].values():
        assert v <= res["john_body_band_upper"]
