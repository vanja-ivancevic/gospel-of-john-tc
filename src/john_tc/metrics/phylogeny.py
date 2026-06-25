"""Our own genealogy of John's witnesses — distance tree + NeighborNet-ready NEXUS export.

Since Münster publishes no CBGM for John, we build the genealogy from our own collation:
pre-genealogical coherence distance -> UPGMA tree (rendered, coloured by family) + a NEXUS
distance block for SplitsTree6 (NeighborNet handles the contaminated, network-like NT
tradition better than a strict tree). No editorial input; fully reproducible.
"""
from __future__ import annotations

from pathlib import Path

from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

from john_tc.config import load_config
from john_tc.metrics.families import assign_families
from john_tc.metrics.genealogy import coherence_distance, informative_mask, reading_matrix

FAMILY_COLORS = {
    "f1": "#d62728", "f13": "#ff7f0e", "Alexandrian": "#1f77b4",
    "Byz": "#7f7f7f", "other": "#2ca02c",
}


def _distance(db_path: Path | None = None):
    wits, codes = reading_matrix(db_path)
    dist = coherence_distance(wits, codes[informative_mask(codes)])
    return wits, dist


def export_nexus(path: Path | None = None, db_path: Path | None = None) -> Path:
    """Write a NEXUS distances block -> open in SplitsTree6 and run NeighborNet."""
    cfg = load_config()
    path = path or cfg.path("reports") / "genealogy" / "john_witnesses.nex"
    path.parent.mkdir(parents=True, exist_ok=True)
    wits, dist = _distance(db_path)
    safe = [w.replace(" ", "_") for w in wits]
    lines = ["#NEXUS", "", "BEGIN taxa;", f"  DIMENSIONS ntax={len(wits)};",
             "  TAXLABELS " + " ".join(safe) + ";", "END;", "",
             "BEGIN distances;", "  FORMAT triangle=both diagonal labels;", "  MATRIX"]
    for i, name in enumerate(safe):
        row = " ".join(f"{dist[i][j]:.4f}" for j in range(len(wits)))
        lines.append(f"  {name} {row}")
    lines += ["  ;", "END;"]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def plot_tree(path: Path | None = None, db_path: Path | None = None) -> Path:
    """Render a UPGMA dendrogram of all witnesses, leaf labels coloured by family."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    cfg = load_config()
    path = path or cfg.path("reports") / "genealogy" / "john_witness_tree.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    wits, dist = _distance(db_path)
    fam = dict(zip(*[assign_families(db_path)[c] for c in ("base_ga", "family")]))
    Z = linkage(squareform(dist, checks=False), method="average")

    fig, ax = plt.subplots(figsize=(11, max(28, len(wits) * 0.16)))
    dendrogram(Z, labels=wits, orientation="left", ax=ax, color_threshold=0,
               above_threshold_color="#bbbbbb", leaf_font_size=6)
    for lbl in ax.get_yticklabels():
        lbl.set_color(FAMILY_COLORS.get(fam.get(lbl.get_text(), "other"), "#000000"))
    ax.set_title("Gospel of John — witness genealogy (pre-genealogical coherence, UPGMA)\n"
                 "leaf colour = manuscript family", fontsize=11)
    ax.set_xlabel("coherence distance (1 − agreement over informative units)")
    ax.legend(handles=[Patch(color=c, label=f) for f, c in FAMILY_COLORS.items()],
              loc="lower left", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def main() -> None:
    nex = export_nexus()
    png = plot_tree()
    print(f"NEXUS (SplitsTree/NeighborNet): {nex}")
    print(f"Tree figure: {png}")


if __name__ == "__main__":
    main()
