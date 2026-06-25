"""Stability heatmap HTML generator — self-contained + correct cell count."""
from __future__ import annotations

import json
import re

import pytest

from john_tc.config import load_config


def test_heatmap_html(tmp_path):
    if not load_config().path("collation_db").exists():
        pytest.skip("collation store not built")
    from john_tc.viz.heatmap import build_heatmap
    out = build_heatmap(path=tmp_path / "hm.html")
    html = out.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html and 'id="grid"' in html
    assert "http://" not in html and "https://" not in html  # self-contained, no external deps
    data = json.loads(re.search(r"const DATA = (\{.*?\});", html).group(1))
    assert len(data) == 879  # one entry per verse
    assert all(len(v) == 3 for v in data.values())  # [stability, anchor%, n_units]
