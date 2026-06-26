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


def test_old_prologue_ch21_claims_do_not_survive(res):
    """Size-matched permutation test (the headline): the old project's Prologue/ch21 'distinct'
    claims are NOT significant. (The Farewell Discourse may register-differ — a genre signal,
    reported honestly, not an authorship claim.)"""
    t = res["section_tests"]
    assert t["prologue"]["seam"] is False
    assert t["ch21"]["seam"] is False
    # every section gets a permutation p with BH correction (a real test, not an eyeballed band)
    for v in t.values():
        assert 0 <= v["p"] <= 1 and "p_fdr" in v
