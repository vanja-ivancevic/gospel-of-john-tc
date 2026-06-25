"""Genealogy-aware instability metrics — structure + substantive checks."""
from __future__ import annotations

import pytest

from john_tc.config import load_config


@pytest.fixture(scope="module")
def chap():
    if not load_config().path("collation_db").exists():
        pytest.skip("collation store not built")
    from john_tc.metrics.weighted_instability import build
    return build()


def test_shape_and_ranges(chap):
    assert len(chap) == 21
    for col in ("flat_instability", "family_instability", "between_family_split"):
        assert col in chap.columns
        assert chap[col].between(0, 1).all()


def test_chapter_21_not_elevated(chap):
    """Refutes the old project's headline: with genealogy-aware data, ch21 is NOT unstable."""
    ch21 = chap.loc[chap.chapter == 21, "family_instability"].iloc[0]
    assert ch21 < chap["family_instability"].mean()


def test_deep_variation_peaks_at_passion(chap):
    """Between-family disagreement (deep variation) is highest in the passion material (ch19)."""
    top = chap.sort_values("between_family_split", ascending=False).chapter.head(3).tolist()
    assert 19 in top
