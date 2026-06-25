"""Family-recovery validation: our collation must reproduce known manuscript families.

This proves the collation carries correct genealogical signal (pre-genealogical coherence),
independent of Münster's CBGM — which has not published genealogical data for John.
"""
from __future__ import annotations

import pytest

from john_tc.config import load_config
from john_tc.metrics.genealogy import build, coherence_distance, informative_mask, reading_matrix


@pytest.fixture(scope="module")
def result():
    if not load_config().path("collation_db").exists():
        pytest.skip("collation store not built")
    return build()


def test_families_recovered(result):
    v = result["validation"]
    assert v["f13"]["monophyletic"], "Family 13 should form a clean monophyletic clade"
    assert v["f1"]["recovered"], "Family 1 should form a compact clade (core + associates)"
    assert v["families_disjoint"], "f1 and f13 clades must be disjoint"
    assert v["all_passed"]


def test_core_f1_pair_is_tight():
    """ms 1 and 1582 are the textbook core f1 pair — must be near-identical."""
    if not load_config().path("collation_db").exists():
        pytest.skip("collation store not built")
    wits, codes = reading_matrix()
    dist = coherence_distance(wits, codes[informative_mask(codes)])
    i, j = wits.index("1"), wits.index("1582")
    assert dist[i][j] < 0.10, f"core f1 pair 1-1582 distance too high: {dist[i][j]:.3f}"
