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
    return total


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

    Includers = base MS extant at the 5:4 units. Omitters = MS extant at neighbouring verses
    (5:3, 5:5) but absent/lacunose at 5:4. Compare dates via a one-sided permutation test.
    """
    cfg = load_config()
    con = duckdb.connect(str(db_path or cfg.path("collation_db")), read_only=True)
    extant = lambda v: set(r[0] for r in con.execute(  # noqa: E731
        """SELECT DISTINCT a.base_ga FROM units u JOIN readings r ON r.app_id=u.app_id
           JOIN attestation a ON a.app_id=r.app_id AND a.reading_id=r.reading_id
           WHERE u.verse_id=? AND u.app_type='main' AND r.reading_type IS DISTINCT FROM 'lac'""",
        [v]).fetchall())
    at_54 = extant("B04K5V4")
    neighbourhood = extant("B04K5V3") | extant("B04K5V5")
    includers = at_54
    omitters = neighbourhood - at_54
    dates = dict(con.execute(
        "SELECT base_ga, date_mid FROM witness_metadata WHERE date_mid IS NOT NULL").fetchall())
    con.close()
    inc = np.array([dates[g] for g in includers if g in dates], dtype=float)
    omt = np.array([dates[g] for g in omitters if g in dates], dtype=float)
    if len(omt) < 3 or len(inc) < 3:
        return {"skipped": "too few dated witnesses", "n_omit": len(omt), "n_incl": len(inc)}
    obs = np.median(omt) - np.median(inc)  # negative => omitters earlier (expected)
    pool = np.concatenate([inc, omt])
    rng = np.random.default_rng(cfg["seed"])
    k = len(omt)
    count = sum(1 for _ in range(10000)
                if (lambda s: np.median(s[:k]) - np.median(s[k:]))(rng.permutation(pool)) <= obs)
    return {
        "n_omit": len(omt), "n_incl": len(inc),
        "median_omitter_date": float(np.median(omt)), "median_includer_date": float(np.median(inc)),
        "difference_years": float(obs), "omitters_earlier": bool(obs < 0),
        "p_value": (count + 1) / 10001,
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
