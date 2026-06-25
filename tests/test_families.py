"""Family-labelling tests: official lists are honoured and Byzantine is collapsed to a block."""
from __future__ import annotations

import pytest

from john_tc.config import load_config
from john_tc.metrics.families import assign_families, witness_weights


@pytest.fixture(scope="module")
def fam():
    if not load_config().path("collation_db").exists():
        pytest.skip("collation store not built")
    return witness_weights(assign_families())


def test_official_families_labelled(fam):
    lut = dict(zip(fam.base_ga, fam.family))
    src = dict(zip(fam.base_ga, fam.family_source))
    # core f1 / f13 members present must carry the asserted (iohannes) label
    for w in ["1", "1582", "118", "209"]:
        assert lut.get(w) == "f1" and src.get(w) == "iohannes_list"
    for w in ["13", "826", "1689"]:
        assert lut.get(w) == "f13" and src.get(w) == "iohannes_list"
    for w in ["P75", "03"]:
        assert lut.get(w) == "Alexandrian"


def test_byzantine_is_the_block(fam):
    counts = fam.family.value_counts()
    assert counts.idxmax() == "Byz", "Byzantine should be the largest family"
    assert counts["Byz"] > counts.drop("Byz").sum() * 0.5  # it dominates the pool


def test_weights_downweight_byzantine(fam):
    # a Byzantine witness must weigh far less than a genealogically isolated 'other' one
    byz_w = fam.loc[fam.family == "Byz", "weight"].iloc[0]
    assert byz_w < 0.05  # ~1/124
    if (fam.family == "other").any():
        assert fam.loc[fam.family == "other", "weight"].iloc[0] == 1.0
