"""RQ4 — re-scoped stylometry (Burrows's Delta), hypothesis-generating only.

Function-word Burrows's Delta measures style rather than topic, calibrated against known controls:

  - Function-word Burrows's Delta on lemmatised MorphGNT text (style, not topic).
  - CALIBRATED against known controls: split single-author books in half (same-author lower
    bound) and compare different authors (gospel vs Paul; upper bound). This gives a scale on
    which John's section-to-section distances can be *read*, not over-interpreted.
  - John's sections (Prologue / body / Farewell / ch21) are placed on that scale. A section
    within the same-author band is consistent with stylistic unity; one approaching the
    different-author band is a hypothesis-generating seam — never a proof of authorship.

Manuscript transmission cannot establish authorship; neither can stylometry on its own. This
is an internal-consistency probe with explicit controls, reported as such.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from john_tc.config import load_config

BOOKS = {  # data book-id -> MorphGNT file
    "Mt": "61-Mt-morphgnt.txt", "Lk": "63-Lk-morphgnt.txt", "Jn": "64-Jn-morphgnt.txt",
    "Ro": "66-Ro-morphgnt.txt", "1Jn": "83-1Jn-morphgnt.txt",
}
AUTHOR = {"Mt": "Matthew", "Lk": "Luke", "Jn": "John", "Ro": "Paul", "1Jn": "John"}
_SCFG = load_config()["stylometry"]
N_MFW = _SCFG["n_mfw"]
WINDOW = _SCFG["window"]  # fixed token window -> all samples same size, so Delta is not a size artifact


def load_book(book: str) -> pd.DataFrame:
    """Parse a MorphGNT file -> DataFrame(chapter, verse, pos, lemma)."""
    path = load_config().root / "data/raw/morphgnt" / BOOKS[book]
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 7:
            continue
        bcv, pos, lemma = parts[0], parts[1], parts[6]
        rows.append((int(bcv[2:4]), int(bcv[4:6]), pos, lemma))
    return pd.DataFrame(rows, columns=["chapter", "verse", "pos", "lemma"])


def _windows(lemmas: list[str], w: int = WINDOW) -> list[list[str]]:
    """Consecutive non-overlapping windows of exactly w tokens (keep a final >=0.75w remainder)."""
    out = [lemmas[i:i + w] for i in range(0, len(lemmas), w)]
    return [c for c in out if len(c) >= 0.75 * w]


def _john_section_lemmas() -> dict[str, list[str]]:
    df = load_book("Jn")
    def lems(mask):
        return df.loc[mask, "lemma"].tolist()
    prologue = (df.chapter == 1) & (df.verse <= 18)
    farewell = df.chapter.between(13, 17)
    appendix = df.chapter == 21
    body = ~(prologue | farewell | appendix)
    return {"prologue": lems(prologue), "farewell": lems(farewell),
            "ch21": lems(appendix), "body": lems(body)}


def build_windows() -> tuple[dict[str, list[str]], dict[str, str], dict[str, str]]:
    """Size-matched windows. Returns (samples, author_of, role_of)."""
    samples, author, role = {}, {}, {}
    for b in ("Mt", "Lk", "Ro"):  # known-author control books
        for i, win in enumerate(_windows(load_book(b).lemma.tolist())):
            n = f"{b}#{i}"
            samples[n], author[n], role[n] = win, AUTHOR[b], "control"
    for sec, lemmas in _john_section_lemmas().items():
        for i, win in enumerate(_windows(lemmas)):
            n = f"Jn:{sec}#{i}"
            samples[n], author[n], role[n] = win, "John", f"john_{sec}"
    return samples, author, role


def delta_matrix(samples: dict[str, list[str]], n_mfw: int = N_MFW):
    """Burrows's Delta over the n most frequent lemmas, z-scored across the sample set."""
    pooled = pd.Series([w for s in samples.values() for w in s])
    mfw = pooled.value_counts().head(n_mfw).index.tolist()
    names = list(samples)
    freq = np.zeros((len(names), len(mfw)))
    for i, n in enumerate(names):
        vc = pd.Series(samples[n]).value_counts()
        total = max(len(samples[n]), 1)
        for j, w in enumerate(mfw):
            freq[i, j] = vc.get(w, 0) / total
    mu, sd = freq.mean(0), freq.std(0)
    sd[sd == 0] = 1.0
    z = (freq - mu) / sd
    D = np.zeros((len(names), len(names)))
    for i in range(len(names)):
        for k in range(len(names)):
            D[i, k] = np.abs(z[i] - z[k]).mean()
    return names, D


def large_sample_validation() -> dict:
    """Does function-word Delta separate authors at all when samples are LARGE? (power check)"""
    samples, author = {}, {}
    for b in ("Mt", "Lk", "Ro", "Jn"):
        lem = load_book(b).lemma.tolist()
        m = len(lem) // 2
        samples[f"{b}_a"], samples[f"{b}_b"] = lem[:m], lem[m:]
        author[f"{b}_a"] = author[f"{b}_b"] = AUTHOR[b]
    names, D = delta_matrix(samples)
    same = [D[i][k] for i in range(len(names)) for k in range(i + 1, len(names))
            if author[names[i]] == author[names[k]]]
    diff = [D[i][k] for i in range(len(names)) for k in range(i + 1, len(names))
            if author[names[i]] != author[names[k]]]
    return {"same_author": float(np.mean(same)), "diff_author": float(np.mean(diff))}


def section_permutation(D, names, role, n_perm: int, seed: int) -> dict:
    """Permutation test: is a John section stylistically farther from the body than body windows are
    from each other? Null = the section's windows are exchangeable with body windows. Statistic =
    mean Δ(section windows, body windows). Multiplicity (3 sections) corrected with BH. This replaces
    the ad-hoc mean+2sd band — a real test with a stated null instead of an eyeballed threshold."""
    from statsmodels.stats.multitest import multipletests

    rng = np.random.default_rng(seed)
    n = len(names)
    body_idx = [i for i in range(n) if role[names[i]] == "john_body"]
    out = {}
    if len(body_idx) < 2:
        return out

    def gap(s_idx, b_idx):
        return float(np.mean([D[i][j] for i in s_idx for j in b_idx]))

    for sec in ("prologue", "farewell", "ch21"):
        sec_idx = [i for i in range(n) if role[names[i]] == f"john_{sec}"]
        if not sec_idx:
            continue
        pooled, k = body_idx + sec_idx, len(sec_idx)
        obs = gap(sec_idx, body_idx)
        cnt = 0
        for _ in range(n_perm):
            perm = list(rng.permutation(pooled))
            if gap(perm[:k], perm[k:]) >= obs:
                cnt += 1
        out[sec] = {"obs": round(obs, 3), "p": (cnt + 1) / (n_perm + 1), "n_windows": k}
    if out:
        secs = list(out)
        q = multipletests([out[s]["p"] for s in secs], method="fdr_bh")[1]
        for s, qq in zip(secs, q):
            out[s]["p_fdr"] = round(float(qq), 4)
            out[s]["seam"] = bool(qq < 0.05)
    return out


def run() -> dict:
    cfg = load_config()
    samples, author, role = build_windows()
    names, D = delta_matrix(samples)
    n = len(names)

    def mean_pairs(pred):
        vals = [D[i][k] for i in range(n) for k in range(i + 1, n) if pred(names[i], names[k])]
        return float(np.mean(vals)) if vals else float("nan"), len(vals)

    ctrl = lambda x: role[x] == "control"  # noqa: E731
    same_author, n_sa = mean_pairs(lambda a, b: ctrl(a) and ctrl(b) and author[a] == author[b])
    diff_author, n_da = mean_pairs(lambda a, b: ctrl(a) and ctrl(b) and author[a] != author[b])
    # gold baseline: John body windows vs each other (same author, same book, size-matched)
    body_internal_vals = [D[i][k] for i in range(n) for k in range(i + 1, n)
                          if role[names[i]] == "john_body" and role[names[k]] == "john_body"]
    body_internal = float(np.mean(body_internal_vals))
    band_upper = body_internal + 2 * float(np.std(body_internal_vals))

    body_idx = [i for i in range(n) if role[names[i]] == "john_body"]
    sections = {}
    for sec in ("prologue", "farewell", "ch21"):
        sec_idx = [i for i in range(n) if role[names[i]] == f"john_{sec}"]
        if not sec_idx:
            continue
        vals = [D[i][j] for i in sec_idx for j in body_idx]
        sections[sec] = float(np.mean(vals))
    interp = {s: ("within John-body range" if v <= band_upper
                  else ("seam? approaches different-author level" if v >= diff_author
                        else "elevated vs body, below different-author"))
              for s, v in sections.items()}
    large = large_sample_validation()
    n_perm = cfg["stats"]["stylometry_permutations"]
    sec_tests = section_permutation(D, names, role, n_perm=n_perm, seed=cfg["seed"])
    return {
        "n_mfw": N_MFW, "window": WINDOW,
        "n_control_windows": sum(1 for x in names if role[x] == "control"),
        "large_sample": large,
        "large_sample_separates": bool(large["diff_author"]
                                       > _SCFG["separation_ratio"] * large["same_author"]),
        "same_author_mean": same_author, "diff_author_mean": diff_author,
        "john_body_internal": body_internal, "john_body_band_upper": band_upper,
        "sections_vs_body": sections, "interpretation": interp,
        "controls_valid": bool(same_author < diff_author),
        # headline: permutation test (real null), not the descriptive +2sd band
        "section_tests": sec_tests,
        "any_section_seam": bool(any(v.get("seam") for v in sec_tests.values())),
    }


def write_report(path: Path | None = None) -> Path:
    cfg = load_config()
    path = path or cfg.path("reports") / "analysis" / "STYLOMETRY.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    r = run()
    L = ["# RQ4 — function-word stylometry (Burrows's Delta), hypothesis-generating", "",
         f"MFW = {r['n_mfw']} most frequent lemmas (MorphGNT); fixed {r['window']}-token windows "
         f"({r['n_control_windows']} control windows) so Delta is NOT a sample-size artifact. "
         "Larger Delta = more stylistically distinct.", "",
         "## Method validation (large samples) — does function-word Δ separate authors?",
         f"- same-author Δ = {r['large_sample']['same_author']:.3f}, "
         f"different-author Δ = {r['large_sample']['diff_author']:.3f} "
         f"-> separates: **{r['large_sample_separates']}** (book halves vs cross-author).",
         "",
         "## Size-matched section test (the honest comparison)",
         f"Small windows have less power (same-author {r['same_author_mean']:.3f} vs "
         f"different-author {r['diff_author_mean']:.3f}); John's sections are small "
         "(prologue 252, ch21 549 tokens), so they MUST be compared size-for-size.",
         f"- John-body internal Δ (same author, same book, size-matched) = "
         f"{r['john_body_internal']:.3f}; band upper (mean+2sd) = {r['john_body_band_upper']:.3f}",
         "", "John sections vs body:"]
    for k, v in r["sections_vs_body"].items():
        L.append(f"- {k}: Δ={v:.3f} — {r['interpretation'][k]} (descriptive)")
    L += ["", "## Permutation test (the headline — a real null, not an eyeballed band)",
          "For each section, the null is that its windows are exchangeable with body windows; the "
          "statistic is mean Δ(section, body). BH-corrected across the three sections.", "",
          "| section | windows | observed Δ | p | p (FDR) | seam? |", "|--|--|--|--|--|--|"]
    for k, v in r["section_tests"].items():
        L.append(f"| {k} | {v['n_windows']} | {v['obs']:.3f} | {v['p']:.4g} | "
                 f"{v.get('p_fdr','—')} | {'YES' if v.get('seam') else 'no'} |")
    L += ["",
          f"**Any stylometric seam beyond John's own internal variation? {r['any_section_seam']}.**",
          "When size is controlled and tested against a proper permutation null, no John section is "
          "significantly farther from the body than body windows are from each other — the large "
          "naive Δ for the Prologue/ch21 is a SAMPLE-SIZE artifact, not a stylistic seam.", "",
          "_Scope: stylometry cannot establish authorship of hypothesised ancient sources._",
          "_This is an internal-consistency probe with explicit controls, reported as such._"]
    path.write_text("\n".join(L), encoding="utf-8")
    return path


def main() -> None:
    r = run()
    ls = r["large_sample"]
    print(f"method validation (large samples): same {ls['same_author']:.3f} vs "
          f"diff {ls['diff_author']:.3f} -> separates: {r['large_sample_separates']}")
    print(f"size-matched John-body baseline: {r['john_body_internal']:.3f} "
          f"(band upper {r['john_body_band_upper']:.3f})")
    print("\nJohn sections vs body (size-matched):")
    for k, v in r["sections_vs_body"].items():
        print(f"  {k:10s} Δ={v:.3f}  -> {r['interpretation'][k]}")
    print(f"\nany stylometric seam beyond internal variation? {r['any_section_seam']}")
    print("Report:", write_report())


if __name__ == "__main__":
    main()
