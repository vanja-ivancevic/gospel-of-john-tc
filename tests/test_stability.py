"""Textual-stability map — ranges + the ch21-is-stable cross-check."""
from __future__ import annotations

import pytest

from john_tc.config import load_config


@pytest.fixture(scope="module")
def s():
    if not load_config().path("collation_db").exists():
        pytest.skip("collation store not built")
    from john_tc.metrics.stability import build
    return build()


def test_consensus_ranges(s):
    assert 0.5 < s["mean_consensus"] <= 1.0
    assert 0 <= s["anchor_frac"] <= 1


def test_ch21_is_not_among_least_stable(s):
    """Consistent with the refutation: ch21 is not a fluid/unstable chapter."""
    assert 21 not in s["least_stable_chapters"]


def test_f13_more_homogeneous_than_alexandrian(s):
    h = s["family_homogeneity"]
    assert h["f13"] > h["Alexandrian"]
