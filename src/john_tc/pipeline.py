"""One-command pipeline: raw ECM apparatus -> every table, figure, and the master report.

    uv run python -m john_tc.pipeline            # full run (genealogy validation B=100)
    uv run python -m john_tc.pipeline --fast     # skip the slow bootstrap validation

Deterministic (seeded in config.yaml). Each stage declares what it produces.
"""
from __future__ import annotations

import sys
import time


def _step(label, fn):
    t = time.perf_counter()
    print(f"[ ] {label} ...", flush=True)
    out = fn()
    print(f"[x] {label}  ({time.perf_counter() - t:.1f}s)" + (f"  {out}" if out else ""), flush=True)


def run(fast: bool = False) -> None:
    from john_tc.analysis.confounds import write_report as confounds_report
    from john_tc.analysis.stylometry import write_report as stylometry_report
    from john_tc.ingest.apparatus import build_db, summary
    from john_tc.metrics import (
        dates, families, genealogy, instability, phylogeny, stability, weighted_instability)
    from john_tc.report import build_report
    from john_tc.validate.genealogy import run as geneal_validate
    from john_tc.validate.genealogy import write_report as geneal_report
    from john_tc.validate.robustness import write_report as robustness_report

    _step("1/14 ingest ECM apparatus -> collation store", lambda: str(summary(build_db())))
    _step("2/14 instability + coverage metrics", lambda: str(instability.build_metric_tables()))
    _step("3/14 family labels + weights", lambda: str(families.build()["family_counts"]))
    _step("4/14 witness dates (NTVMR)", lambda: str(dates.enrich_metadata()))
    _step("5/14 genealogy clustering", lambda: str(genealogy.build()["validation"]["all_passed"]))
    _step("6/14 genealogy-aware instability", lambda: f"{len(weighted_instability.build())} chapters")
    _step("7/14 textual-stability map", lambda: str(stability.build()["anchor_units"]) + " anchors")
    _step("8/14 phylogeny tree + NEXUS", lambda: phylogeny.export_nexus() and str(phylogeny.plot_tree()))
    _step("9/14 instability figure", lambda: str(weighted_instability.plot_comparison()))
    _step("10/14 confound regression report", lambda: str(confounds_report()))
    _step("11/14 stylometry (RQ4) report", lambda: str(stylometry_report()))
    _step("12/14 stability map report", lambda: str(stability.write_report()))
    from john_tc.viz.heatmap import build_heatmap
    _step("12b/14 stability heatmap (HTML)", lambda: str(build_heatmap()))
    B = 8 if fast else 100
    Bb = 80 if fast else 500
    _step(f"13/14 genealogy validation (B={B})", lambda: str(geneal_report(geneal_validate(B=B))))
    _step(f"13b/14 robustness stress-test (B={Bb})", lambda: str(robustness_report(B=Bb)))
    _step("14/14 master report", lambda: str(build_report()))
    from john_tc.site.export_data import export
    _step("14b/14 export dashboard data (site/)", lambda: str(export()))
    print("\nDone. See reports/REPORT.md and the dashboard in site/ "
          "(cd site && python3 -m http.server).")


def main() -> None:
    run(fast="--fast" in sys.argv)


if __name__ == "__main__":
    main()
