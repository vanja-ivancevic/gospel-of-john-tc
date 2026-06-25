"""Robustness stress-test — the headline findings must survive resampling/perturbation."""
from __future__ import annotations

import pytest

from john_tc.config import load_config


@pytest.fixture(scope="module")
def r():
    if not load_config().path("collation_db").exists():
        pytest.skip("collation store not built")
    from john_tc.validate.robustness import run
    return run(B=80)


def test_map_not_driven_by_one_family(r):
    loo = r["leave_one_family_out"]
    assert loo["min_spearman"] >= 0.8
    assert loo["ch21_stays_low"]


def test_confound_effects_are_robust(r):
    c = r["confounds"]
    assert c["prologue_robust_negative"], f"prologue CI {c['prologue_ci']} not robustly negative"
    assert c["synoptic_robust_positive"], f"synoptic CI {c['synoptic_ci']} not robustly positive"


def test_overall_verdict(r):
    assert r["all_robust"] is True
