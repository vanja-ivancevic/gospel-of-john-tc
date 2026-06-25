"""Date integration + the John 5:4 early-omission regression test (permanent gate)."""
from __future__ import annotations

import pytest

from john_tc.config import load_config
from john_tc.metrics.dates import ga_to_docid, parse_orig


@pytest.mark.parametrize("ga,doc", [
    ("P66", 10066), ("P75", 10075), ("01", 20001), ("03", 20003),
    ("019", 20019), ("1", 30001), ("13", 30013), ("1582", 31582), ("L1000", 41000),
])
def test_ga_to_docid(ga, doc):
    assert ga_to_docid(ga) == doc


@pytest.mark.parametrize("orig,early,late", [
    ("XII", 1100, 1199),
    ("VI/VII", 500, 699),
    ("III (A)", 200, 299),
    ("948", 948, 948),
    ("948.0", 948, 948),
    ("X/XI", 900, 1099),
    ("", None, None),
])
def test_parse_orig(orig, early, late):
    assert parse_orig(orig) == (early, late)


@pytest.fixture(scope="module")
def signal():
    if not load_config().path("collation_db").exists():
        pytest.skip("collation store not built")
    from john_tc.metrics.dates import enrich_metadata, five_four_date_signal
    enrich_metadata()
    return five_four_date_signal()


def test_john_5_4_omitters_are_earlier(signal):
    """The classic interpolation: omitters of 5:4 must be significantly EARLIER than includers."""
    assert "skipped" not in signal, signal
    assert signal["omitters_earlier"], "5:4 omitters should predate includers"
    assert signal["p_value"] < 0.01, f"5:4 date signal not significant (p={signal['p_value']})"
    assert signal["median_omitter_date"] < signal["median_includer_date"] - 200
