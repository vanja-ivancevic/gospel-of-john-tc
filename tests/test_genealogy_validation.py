"""Genealogy validation gate — must pass before any downstream analysis trusts the families."""
from __future__ import annotations

import pytest

from john_tc.config import load_config


@pytest.fixture(scope="module")
def res():
    if not load_config().path("collation_db").exists():
        pytest.skip("collation store not built")
    from john_tc.validate.genealogy import run
    return run(B=8)  # small bootstrap; f13/f1-core are deterministic enough at this size


def test_every_official_family_is_a_real_cluster(res):
    # positive silhouette => members are closer to each other than to other families
    for fam, s in res["silhouette"]["by_family"].items():
        assert s > 0, f"{fam} not a real cluster (silhouette {s})"


def test_tight_families_have_bootstrap_support(res):
    assert res["bootstrap_support"]["f13"] >= 0.7
    assert res["bootstrap_support"]["f1_core"] >= 0.7


def test_clusters_match_official_labels(res):
    assert res["cluster_match"]["ari"] >= 0.5


def test_recovery_is_robust_to_parameters(res):
    assert all(r["f1"] and r["f13"] for r in res["sensitivity"])


def test_overall_gate(res):
    assert res["passed"] is True
