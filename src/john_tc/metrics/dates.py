"""Witness dates from the INTF Kurzgefasste Liste (NTVMR) — the proper fix for John 5:4.

Family alone can't isolate the 5:4 omission (it mixes early omitters with late includers).
Dates can: the angel/pool clause (5:4) is omitted by the EARLIEST witnesses and added by the
later Byzantine mass. This module joins NTVMR dates by docID (the unambiguous key — GA numbers
collide across majuscule/minuscule/papyrus/lectionary) and provides the early-omission test.

NTVMR docID convention: papyri 1xxxx, majuscules 2xxxx, minuscules 3xxxx, lectionaries 4xxxx.
`orig` is a Roman-numeral century ("XII", "VI/VII", "III (A)") or an explicit year ("948").
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import duckdb
import numpy as np

from john_tc.config import load_config

_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def ga_to_docid(ga: str) -> int | None:
    """Map a Gregory-Aland siglum to the NTVMR docID (disambiguates type by leading form)."""
    try:
        if ga.startswith("P"):
            return 10000 + int(ga[1:])
        if ga.startswith("L"):
            return 40000 + int(ga[1:])
        if ga[0] == "0":           # majuscule: leading zero (01, 022, 0141)
            return 20000 + int(ga)
        return 30000 + int(ga)     # minuscule (1, 13, 1582)
    except ValueError:
        return None


def _roman_to_int(s: str) -> int | None:
    s = s.strip().upper()
    if not s or any(c not in _ROMAN for c in s):
        return None
    total, prev = 0, 0
    for c in reversed(s):
        v = _ROMAN[c]
        total += -v if v < prev else v
        prev = max(prev, v)
    # fail closed: reject non-canonical numerals (e.g. "IIII", "VV") rather than returning a
    # plausible-but-wrong century — a malformed Liste entry should be dropped, not mis-dated.
    if _int_to_roman(total) != s:
        return None
    return total


def _int_to_roman(n: int) -> str:
    if n <= 0:
        return ""
    vals = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
            (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = []
    for v, sym in vals:
        while n >= v:
            out.append(sym)
            n -= v
    return "".join(out)


def parse_orig(orig: str) -> tuple[int | None, int | None]:
    """'XII'->(1100,1199); 'VI/VII'->(500,699); 'III (A)'->(200,299); '948'->(948,948)."""
    if orig is None:
        return None, None
    s = re.sub(r"\(.*?\)", "", str(orig)).strip()  # drop qualifiers like "(A)"
    if not s:
        return None, None
    # explicit year (possibly "948.0")
    m = re.fullmatch(r"(\d{3,4})(?:\.0)?", s)
    if m:
        y = int(m.group(1))
        return y, y
    parts = [p.strip() for p in s.split("/")]
    cents = [_roman_to_int(p) for p in parts]
    cents = [c for c in cents if c]
    if not cents:
        return None, None
    return (min(cents) - 1) * 100, max(cents) * 100 - 1


def load_liste(path: Path | None = None) -> dict[int, str]:
    cfg = load_config()
    path = path or cfg.root / "data/raw/ntvmr/liste.csv"
    out: dict[int, str] = {}
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            doc = row.get("manuscripts.manuscript.docID", "")
            try:
                docid = int(float(doc))
            except (ValueError, TypeError):
                continue
            out[docid] = row.get("manuscripts.manuscript.orig", "")
    return out


def enrich_metadata(db_path: Path | None = None) -> dict:
    """Add date_early/date_late/date_mid to witness_metadata from the NTVMR Liste."""
    cfg = load_config()
    db_path = db_path or cfg.path("collation_db")
    liste = load_liste()
    con = duckdb.connect(str(db_path))
    gas = [r[0] for r in con.execute("SELECT base_ga FROM witness_metadata").fetchall()]
    rows = []
    for ga in gas:
        doc = ga_to_docid(ga)
        early, late = parse_orig(liste.get(doc)) if doc else (None, None)
        mid = (early + late) // 2 if early is not None else None
        rows.append((ga, doc, early, late, mid))
    con.execute("CREATE OR REPLACE TEMP TABLE _dates(base_ga VARCHAR, docid INT, "
                "date_early INT, date_late INT, date_mid INT)")
    con.executemany("INSERT INTO _dates VALUES (?,?,?,?,?)", rows)
    con.execute("ALTER TABLE witness_metadata DROP COLUMN IF EXISTS date_early")
    con.execute("ALTER TABLE witness_metadata DROP COLUMN IF EXISTS date_late")
    con.execute("ALTER TABLE witness_metadata DROP COLUMN IF EXISTS date_mid")
    con.execute("ALTER TABLE witness_metadata DROP COLUMN IF EXISTS docid")
    con.execute("""CREATE OR REPLACE TABLE witness_metadata AS
                   SELECT m.*, d.docid, d.date_early, d.date_late, d.date_mid
                   FROM witness_metadata m LEFT JOIN _dates d USING(base_ga)""")
    n_dated = con.execute("SELECT count(*) FROM witness_metadata WHERE date_mid IS NOT NULL").fetchone()[0]
    con.close()
    return {"witnesses": len(gas), "dated": n_dated}


def five_four_date_signal(db_path: Path | None = None) -> dict:
    """Test the known truth: witnesses OMITTING John 5:4 are earlier than those including it.

    Includers = witnesses attesting substantive 5:4 text. Omitters = witnesses present in the
    neighbourhood (5:3/5:5) or carrying an explicit `om` at 5:4, but NOT attesting substantive 5:4
    text — with witnesses explicitly lacunose at 5:4 removed, so a damaged page is not mistaken for
    a deliberate omission (the lacuna-contamination the set-subtraction approach risked). Reported on
    the date midpoint and, as a censoring sensitivity check, on the latest-possible date;
    significance by one-sided permutation and a tie-robust Mann–Whitney.
    """
    cfg = load_config()
    con = duckdb.connect(str(db_path or cfg.path("collation_db")), read_only=True)

    def _wits(verse_id, where):
        return set(r[0] for r in con.execute(
            f"""SELECT DISTINCT a.base_ga FROM units u JOIN readings r ON r.app_id=u.app_id
                JOIN attestation a ON a.app_id=r.app_id AND a.reading_id=r.reading_id
                WHERE u.verse_id='{verse_id}' AND u.app_type='main' AND a.base_ga<>'basetext'
                      AND {where}""").fetchall())
    substantive = _wits("B04K5V4", "r.reading_type IS NULL")        # genuine 5:4 text
    om_wits = _wits("B04K5V4", "r.reading_type='om'")               # explicit omission
    lac_54 = _wits("B04K5V4", "r.reading_type='lac'")               # damaged here -> exclude
    neighbourhood = (_wits("B04K5V3", "r.reading_type IS DISTINCT FROM 'lac'")
                     | _wits("B04K5V5", "r.reading_type IS DISTINCT FROM 'lac'"))
    includers = substantive
    omitters = (neighbourhood | om_wits) - substantive - lac_54
    meta = {g: (dm, dl) for g, dm, dl in con.execute(
        "SELECT base_ga, date_mid, date_late FROM witness_metadata "
        "WHERE date_mid IS NOT NULL").fetchall()}
    con.close()

    rng = np.random.default_rng(cfg["seed"])

    def _signal(field_idx):  # 0 = midpoint, 1 = latest-possible (censoring sensitivity)
        inc = np.array([meta[g][field_idx] for g in includers if g in meta], dtype=float)
        omt = np.array([meta[g][field_idx] for g in omitters if g in meta], dtype=float)
        if len(omt) < 3 or len(inc) < 3:
            return None, inc, omt
        obs = np.median(omt) - np.median(inc)
        pool = np.concatenate([inc, omt])
        k = len(omt)
        count = sum(1 for _ in range(10000)
                    if (lambda s: np.median(s[:k]) - np.median(s[k:]))(rng.permutation(pool)) <= obs)
        return (obs, (count + 1) / 10001), inc, omt

    res_mid, inc, omt = _signal(0)
    if res_mid is None:
        return {"skipped": "too few dated witnesses", "n_omit": len(omt), "n_incl": len(inc)}
    obs, p = res_mid
    res_late, _, _ = _signal(1)
    try:
        from scipy.stats import mannwhitneyu
        mw_p = float(mannwhitneyu(omt, inc, alternative="less").pvalue)
    except Exception:  # pragma: no cover
        mw_p = None
    return {
        "n_omit": len(omt), "n_incl": len(inc),
        "median_omitter_date": float(np.median(omt)), "median_includer_date": float(np.median(inc)),
        "difference_years": float(obs), "omitters_earlier": bool(obs < 0),
        "p_value": p, "mannwhitney_p": mw_p,
        "p_value_latest_date": (res_late[1] if res_late else None),
    }


def main() -> None:
    print("Enriching witness_metadata with NTVMR dates:", enrich_metadata())
    s = five_four_date_signal()
    print("\nJohn 5:4 early-omission test:")
    if s.get("skipped"):
        print("  SKIPPED:", s)
        return
    print(f"  omitters (n={s['n_omit']}) median date {s['median_omitter_date']:.0f} "
          f"vs includers (n={s['n_incl']}) median {s['median_includer_date']:.0f}")
    print(f"  Δ={s['difference_years']:.0f} yrs, omitters earlier={s['omitters_earlier']}, "
          f"p={s['p_value']:.4g}")
    print(f"\n5:4 DATE SIGNAL: {'RECOVERED' if s['omitters_earlier'] and s['p_value']<0.05 else 'not found'}")


if __name__ == "__main__":
    main()
