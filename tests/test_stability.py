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


def test_family_vote_metric_present(s):
    # the "weighed" headline metric exists alongside the raw "counted" one
    assert 0.5 < s["mean_family_consensus"] <= 1.0
    assert s["family_anchor_units"] > 0


def test_no_corrector_double_count():
    """Flat metric counts one reading per (unit, witness): n_lemma + n_diverge never exceeds
    n_extant (an intra-manuscript corrector artifact that would otherwise inflate it)."""
    import duckdb

    from john_tc.metrics.instability import _UNIT_SQL
    con = duckdb.connect(str(load_config().path("collation_db")), read_only=True)
    bad = con.execute(
        f"SELECT count(*) FROM ({_UNIT_SQL}) t WHERE n_lemma + n_diverge > n_extant"
    ).fetchone()[0]
    con.close()
    assert bad == 0


def test_ch21_is_not_among_least_stable(s):
    """Chapter 21 is not a fluid/unstable chapter."""
    assert 21 not in s["least_stable_chapters"]


def test_f13_more_homogeneous_than_alexandrian(s):
    h = s["family_homogeneity"]
    assert h["f13"] > h["Alexandrian"]
