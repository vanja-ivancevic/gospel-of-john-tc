"""Phylogeny of John's witnesses — distance + character exports and a Neighbor-Joining tree.

Built entirely from our own collation (no editorial input, fully reproducible). Three artifacts:

  - a NEXUS **distance** block for SplitsTree6 NeighborNet (the network method handles the
    contaminated, non-tree-like NT tradition better than a strict tree);
  - a NEXUS **character matrix** (witnesses x informative units, readings as discrete states) — the
    input parsimony / Bayesian phylogenetics expect, the same kind of matrix Edmondson (2019) and the
    open-cbgm/teiphy toolchain use, so the data can be taken straight into PAUP*/MrBayes/SplitsTree;
  - a **Neighbor-Joining** tree (Newick + rendered figure). NJ drops the ultrametric/molecular-clock
    assumption that UPGMA makes, which manuscripts plainly violate, so it is the better-grounded
    distance tree. The Newick string is the deterministic, citable artifact.

The witness groupings here are compared against Edmondson's published phylogeny of John (see
reports/genealogy/VALIDATION.md): an independent method recovering the same families is the point.
"""
from __future__ import annotations

import io
from pathlib import Path

from john_tc.config import load_config
from john_tc.metrics.families import assign_families
from john_tc.metrics.genealogy import coherence_distance, informative_mask, reading_matrix

FAMILY_COLORS = {
    "f1": "#d62728", "f13": "#ff7f0e", "Alexandrian": "#1f77b4",
    "Byz": "#7f7f7f", "other": "#2ca02c",
}
# NEXUS Standard-datatype symbols (62 states); units with more readings than this are dropped.
_SYMBOLS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


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


def export_character_nexus(path: Path | None = None, db_path: Path | None = None) -> Path:
    """Write a NEXUS character matrix (Standard datatype) of the informative units.

    Each informative variation unit becomes one character; its readings are relabelled to local
    state symbols (0,1,2,...); a witness not extant at the unit is '?'. This is the matrix to load
    into MrBayes / PAUP* / SplitsTree for parsimony, Bayesian, or NeighborNet analysis.
    """
    import numpy as np
    cfg = load_config()
    path = path or cfg.path("reports") / "genealogy" / "john_witnesses_characters.nex"
    path.parent.mkdir(parents=True, exist_ok=True)
    wits, codes = reading_matrix(db_path)
    inf = codes[informative_mask(codes)]                       # (units x witnesses)
    safe = [w.replace(" ", "_") for w in wits]
    rows = [""] * len(wits)
    kept = 0
    for unit in inf:                                           # one character per informative unit
        present = np.unique(unit[unit >= 0])
        if present.size > len(_SYMBOLS):                       # too many readings for Standard symbols
            continue
        remap = {code: _SYMBOLS[k] for k, code in enumerate(present)}
        for wi, c in enumerate(unit):
            rows[wi] += remap[c] if c >= 0 else "?"
        kept += 1
    width = max(len(s) for s in safe)
    body = "\n".join(f"  {name.ljust(width)}  {seq}" for name, seq in zip(safe, rows))
    text = (f"#NEXUS\n\nBEGIN data;\n  DIMENSIONS ntax={len(wits)} nchar={kept};\n"
            f'  FORMAT datatype=Standard symbols="{_SYMBOLS}" gap=- missing=?;\n'
            f"  MATRIX\n{body}\n  ;\nEND;\n")
    path.write_text(text, encoding="utf-8")
    return path


def _nj_tree(db_path: Path | None = None):
    """Neighbor-Joining tree from the coherence distance (Biopython). Deterministic."""
    from Bio.Phylo.TreeConstruction import DistanceMatrix, DistanceTreeConstructor
    wits, dist = _distance(db_path)
    names = [w.replace(" ", "_") for w in wits]
    ltm = [[float(dist[i][j]) for j in range(i + 1)] for i in range(len(names))]
    tree = DistanceTreeConstructor().nj(DistanceMatrix(names=names, matrix=ltm))
    tree.ladderize()
    return wits, tree


def export_newick(path: Path | None = None, db_path: Path | None = None) -> Path:
    """Write the Neighbor-Joining tree as Newick (the deterministic, citable artifact)."""
    from Bio import Phylo
    cfg = load_config()
    path = path or cfg.path("reports") / "genealogy" / "john_witnesses_nj.nwk"
    path.parent.mkdir(parents=True, exist_ok=True)
    _, tree = _nj_tree(db_path)
    buf = io.StringIO()
    Phylo.write(tree, buf, "newick")
    path.write_text(buf.getvalue(), encoding="utf-8")
    return path


def plot_tree(path: Path | None = None, db_path: Path | None = None) -> Path:
    """Render the Neighbor-Joining tree, leaf labels coloured by manuscript family."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from Bio import Phylo
    from matplotlib.patches import Patch

    cfg = load_config()
    path = path or cfg.path("reports") / "genealogy" / "john_witness_tree.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    wits, tree = _nj_tree(db_path)
    fam = dict(zip(*[assign_families(db_path)[c] for c in ("base_ga", "family")]))
    colour = {w.replace(" ", "_"): FAMILY_COLORS.get(fam.get(w, "other"), "#000000") for w in wits}

    fig, ax = plt.subplots(figsize=(11, max(28, len(wits) * 0.16)))
    Phylo.draw(tree, axes=ax, do_show=False, label_colors=lambda n: colour.get(n, "#000000"),
               branch_labels=lambda c: "")
    ax.set_title("Gospel of John — witness phylogeny (pre-genealogical coherence, Neighbor-Joining)\n"
                 "leaf colour = manuscript family", fontsize=11)
    ax.legend(handles=[Patch(color=c, label=f) for f, c in FAMILY_COLORS.items()],
              loc="lower left", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def main() -> None:
    print(f"NEXUS distances (SplitsTree/NeighborNet): {export_nexus()}")
    print(f"NEXUS characters (MrBayes/PAUP*):         {export_character_nexus()}")
    print(f"Newick (Neighbor-Joining):                {export_newick()}")
    print(f"Tree figure:                              {plot_tree()}")


if __name__ == "__main__":
    main()
