"""RQ2 confound model — covariate construction + robust findings."""
from __future__ import annotations

import pytest

from john_tc.analysis.confounds import _is_synoptic, _section
from john_tc.config import load_config


def test_section_assignment():
    assert _section(1, 1) == "prologue"
    assert _section(1, 19) == "body"
    assert _section(15, 1) == "farewell"
    assert _section(21, 1) == "appendix"
    assert _section(3, 16) == "body"


def test_synoptic_flags():
    assert _is_synoptic(6, 10)        # feeding of the 5000
    assert _is_synoptic(19, 18)       # crucifixion
    assert not _is_synoptic(3, 16)    # unique to John


@pytest.fixture(scope="module")
def res():
    if not load_config().path("collation_db").exists():
        pytest.skip("collation store not built")
    from john_tc.analysis.confounds import run
    return run("between_family_split")


def test_prologue_is_stable_after_controls(res):
    """Prologue shows LESS deep variation, robust to confounds (FDR-significant, negative)."""
    coefs = res["coefficients"]
    prologue = coefs.loc[coefs.index.str.contains("prologue")]
    assert prologue["coef"].iloc[0] < 0
    assert prologue["p_fdr"].iloc[0] < 0.05


def test_synoptic_parallels_drive_disagreement(res):
    """Harmonisation: verses with Synoptic parallels show MORE between-family disagreement."""
    syn = res["coefficients"].loc["synoptic"]
    assert syn["coef"] > 0 and syn["p_fdr"] < 0.05


def test_appendix_not_distinctive(res):
    """Chapter 21 is not special once confounds and the Prologue are accounted for."""
    appx = res["coefficients"].loc[res["coefficients"].index.str.contains("appendix")]
    assert appx["p_fdr"].iloc[0] > 0.05
