"""The hard validation gate: known interpolations must register in the correct direction.

This is the CI guardrail against the failure that sank the previous project — a metric
that called the Pericope Adulterae *less* anomalous than its context.
"""
from __future__ import annotations

import pytest

from john_tc.config import load_config
from john_tc.validate.interpolations import run_gate


@pytest.fixture(scope="module")
def gate():
    if not load_config().path("collation_db").exists():
        pytest.skip("collation store not built; run `python -m john_tc.ingest.apparatus`")
    # fewer permutations for test speed; p-value still resolves the PA effect
    return run_gate(n_perm=2000)


def test_pericope_adulterae_is_omitted(gate):
    pa = gate["pericope_adulterae"]
    assert pa["direction_lower"], "PA must have LOWER coverage than the rest of John"
    assert pa["p_value"] < 0.01, f"PA omission not significant (p={pa['p_value']})"
    # PA attested by far fewer manuscripts than context (~80 vs ~140)
    assert pa["target_mean"] < 0.7 * pa["rest_mean"]


def test_gate_passes(gate):
    assert gate["gate_passed"] is True
