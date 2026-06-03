"""Stage 7 — validate the built SQLite artifact and print a coverage report.

    python -m pipeline.validate --scope core

Sanity checks (per PLAN.md). Exits non-zero if a hard check fails.
"""

import argparse
import sqlite3
import sys

from . import sources as S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=["core", "full"], default="core")
    args = ap.parse_args()

    db_path = S.ROOT / S.db_filename(args.scope)
    if not db_path.exists():
        S.log(f"ERROR: {db_path} does not exist; run build_sqlite first.")
        raise SystemExit(1)
    conn = sqlite3.connect(db_path)
    q = lambda sql, *a: conn.execute(sql, a).fetchone()[0]

    failures = []
    warnings = []

    n_chars = q("SELECT COUNT(*) FROM characters")
    n_core = q("SELECT COUNT(*) FROM characters WHERE is_core=1")
    n_comp = q("SELECT COUNT(*) FROM compounds")
    n_edges = q("SELECT COUNT(*) FROM character_compounds")
    n_en = q("SELECT COUNT(*) FROM compounds WHERE has_english=1")

    print(f"\n{'='*60}\n  {db_path.name} — validation ({args.scope})\n{'='*60}")
    print(f"characters:          {n_chars}  (core={n_core})")
    print(f"compounds:           {n_comp}  (with English: {n_en} = "
          f"{100*n_en//max(n_comp,1)}%)")
    print(f"character_compounds: {n_edges} edges")

    # 1. Every character has at least one reading.
    no_reading = q("SELECT COUNT(*) FROM characters c "
                   "WHERE NOT EXISTS (SELECT 1 FROM character_readings r WHERE r.hanja=c.hanja)")
    (failures if no_reading else print)(
        f"FAIL: {no_reading} characters have no reading" if no_reading
        else "OK: every character has >=1 reading")

    # 2. Every character_compounds edge references a real character & compound.
    bad_edge = q("SELECT COUNT(*) FROM character_compounds cc "
                 "WHERE NOT EXISTS (SELECT 1 FROM characters c WHERE c.hanja=cc.hanja) "
                 "OR NOT EXISTS (SELECT 1 FROM compounds k WHERE k.id=cc.compound_id)")
    if bad_edge:
        failures.append(f"{bad_edge} dangling character_compounds edges")
    else:
        print("OK: all edges reference valid characters and compounds")

    # 3. definition_ko present for >99% of compounds.
    no_def = q("SELECT COUNT(*) FROM compounds WHERE definition_ko IS NULL OR definition_ko=''")
    pct_def = 100 * (n_comp - no_def) // max(n_comp, 1)
    if pct_def < 99:
        warnings.append(f"only {pct_def}% of compounds have a Korean definition "
                        f"({no_def} missing)")
    else:
        print(f"OK: {pct_def}% of compounds have a Korean definition")

    # 4. Characters with zero compounds (informational).
    orphan_chars = q("SELECT COUNT(*) FROM characters c "
                     "WHERE NOT EXISTS (SELECT 1 FROM character_compounds cc WHERE cc.hanja=c.hanja)")
    if orphan_chars:
        warnings.append(f"{orphan_chars} characters have no compounds yet")

    # 5. Spot-check 學: should have many compounds incl. English ones.
    rows = conn.execute(
        "SELECT cp.word_ko, cp.english_gloss FROM compounds cp "
        "JOIN character_compounds cc ON cc.compound_id=cp.id "
        "WHERE cc.hanja='學' AND cp.has_english=1 ORDER BY cp.id LIMIT 8").fetchall()
    print(f"\nspot-check 學 (with English), {len(rows)} shown:")
    for w, g in rows:
        print(f"   {w:8s} {g or ''}")

    # Multi-reading spot check.
    for h in ("不", "例", "樂"):
        c = q("SELECT COUNT(*) FROM character_compounds WHERE hanja=?", h)
        print(f"   {h}: {c} compounds")

    # Per-syllable / per-reading coverage table (top + bottom).
    print("\nper-primary-sound coverage (chars / total compounds), top 12:")
    for sound, nc, comp in conn.execute(
        "SELECT c.primary_sound, COUNT(DISTINCT c.hanja), COUNT(cc.compound_id) "
        "FROM characters c LEFT JOIN character_compounds cc ON cc.hanja=c.hanja "
        "GROUP BY c.primary_sound ORDER BY COUNT(cc.compound_id) DESC LIMIT 12"):
        print(f"   {sound or '?':4s}  chars={nc:3d}  compounds={comp}")

    conn.close()

    print(f"\n{'-'*60}")
    for w in warnings:
        print(f"WARN: {w}")
    if failures:
        for fmsg in failures:
            print(f"FAIL: {fmsg}")
        print(f"\n{len(failures)} hard check(s) failed.")
        sys.exit(1)
    print("All hard checks passed." + (f" ({len(warnings)} warning(s))" if warnings else ""))


if __name__ == "__main__":
    main()
