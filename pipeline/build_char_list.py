"""Stage 1 — build the master character list.

    python -m pipeline.build_char_list --scope core   # 한문교육용 기초한자 (~1,799)
    python -m pipeline.build_char_list --scope full    # + rycont 5,978

Outputs:
  staging/characters.jsonl  — one record per character (with its readings)
  staging/syllables.txt     — unique scrape syllables (readings + 두음법칙 variants)

Every Hanja is NFC-normalized. rycont metadata is joined on the NFC key, with a
small 정자→약자 variant map (data/backfill_chars.json) for the handful of core
glyphs rycont stores under a different unified codepoint.
"""

import argparse
import ast
import csv
import json

from . import sources as S


def parse_meaning_literal(raw):
    """rycont 'meaning' is a stringified literal: [[[meanings],[readings]], ...].
    Return a list of (meanings:list[str], readings:list[str]) pairs."""
    try:
        parsed = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return []
    pairs = []
    for pair in parsed:
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            meanings = [str(m) for m in pair[0]]
            readings = [S.nfc(str(r)) for r in pair[1]]
            pairs.append((meanings, readings))
    return pairs


def load_rycont():
    """Return dict: NFC hanja -> parsed rycont record."""
    out = {}
    with open(S.RYCONT_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            h = S.nfc((row.get("hanja") or "").strip())
            if not h:
                continue
            pairs = parse_meaning_literal(row.get("meaning") or "")
            out[h] = {
                "hanja": h,
                "main_sound": S.nfc((row.get("main_sound") or "").strip()),
                "level": (row.get("level") or "").strip() or None,
                "radical": (row.get("radical") or "").strip() or None,
                "strokes": _to_int(row.get("strokes")),
                "total_strokes": _to_int(row.get("total_strokes")),
                "meaning_pairs": pairs,
            }
    return out


def _to_int(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def reading_meaning_map(pairs):
    """reading -> 'meaning, meaning' joined from the meaning pairs."""
    rm = {}
    for meanings, readings in pairs:
        gloss = ", ".join(meanings)
        for r in readings:
            rm.setdefault(r, gloss)
    return rm


def build_record(hanja, primary_sound, is_core, core_level, source, ry, extra_readings=()):
    """Assemble one character record. ``ry`` is the joined rycont row or None.
    ``extra_readings`` are readings to include beyond rycont's (e.g. the MOE
    reading) even if rycont doesn't list them."""
    rm = reading_meaning_map(ry["meaning_pairs"]) if ry else {}

    readings_set = set(rm) | {r for r in extra_readings if r}
    if primary_sound:
        readings_set.add(primary_sound)
    if not primary_sound:
        primary_sound = (ry or {}).get("main_sound") or (sorted(readings_set)[0] if readings_set else None)
        if primary_sound:
            readings_set.add(primary_sound)

    readings = [{
        "reading": r,
        "meaning_ko": rm.get(r),
        "is_primary": 1 if r == primary_sound else 0,
    } for r in sorted(readings_set)]

    meaning_ko = rm.get(primary_sound) or (next(iter(rm.values()), None))

    return {
        "hanja": hanja,
        "primary_sound": primary_sound,
        "level": (ry or {}).get("level"),
        "is_core": 1 if is_core else 0,
        "core_level": core_level,
        "meaning_ko": meaning_ko,
        "radical": (ry or {}).get("radical"),
        "strokes": (ry or {}).get("strokes"),
        "total_strokes": (ry or {}).get("total_strokes"),
        "source": source,
        "readings": readings,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=["core", "full"], default="core")
    args = ap.parse_args()
    S.ensure_dirs()

    rycont = load_rycont()
    S.log(f"rycont: {len(rycont)} characters loaded")

    backfill = json.loads((S.DATA / "backfill_chars.json").read_text(encoding="utf-8"))
    variant_map = {S.nfc(k): S.nfc(v) for k, v in backfill.get("variant_to_rycont", {}).items()}

    def ry_for(h):
        if h in rycont:
            return rycont[h]
        v = variant_map.get(h)
        return rycont.get(v) if v else None

    records = {}  # hanja -> record

    # ── Core: the MOE 한문교육용 기초한자 ──────────────────────────────
    core_rows = list(csv.DictReader(open(S.DATA / "core_1800.csv", encoding="utf-8")))
    for row in core_rows:
        h = S.nfc(row["hanja"].strip())
        reading = S.nfc(row["reading"].strip())
        core_level = (row.get("core_level") or "").strip() or None
        records[h] = build_record(
            h, primary_sound=reading, is_core=True, core_level=core_level,
            source="core", ry=ry_for(h), extra_readings=[reading],
        )
    S.log(f"core: {len(records)} characters")
    matched = sum(1 for h in records if ry_for(h))
    S.log(f"core: {matched}/{len(records)} joined to rycont metadata "
          f"({len(records) - matched} without radical/strokes)")

    # ── Full: union in all remaining rycont characters ────────────────
    if args.scope == "full":
        added = 0
        for h, ry in rycont.items():
            if h in records:
                continue
            records[h] = build_record(
                h, primary_sound=ry["main_sound"], is_core=False, core_level=None,
                source="rycont", ry=ry,
            )
            added += 1
        S.log(f"full: added {added} rycont characters (total {len(records)})")

    # ── Backfill chars (chars referenced by compounds but in neither list) ──
    for h, info in backfill.get("chars", {}).items():
        h = S.nfc(h)
        if h in records:
            continue
        ry = ry_for(h)
        rec = build_record(
            h, primary_sound=S.nfc(info.get("reading", "")) or None,
            is_core=False, core_level=None, source="backfill", ry=ry,
            extra_readings=[S.nfc(info.get("reading", ""))],
        )
        # Allow the backfill file to override metadata when rycont has none.
        for k in ("radical", "strokes", "total_strokes", "meaning_ko"):
            if rec.get(k) is None and info.get(k) is not None:
                rec[k] = info[k]
        records[h] = rec

    # ── Emit ──────────────────────────────────────────────────────────
    chars = sorted(records.values(), key=lambda r: r["hanja"])
    with open(S.STAGING / "characters.jsonl", "w", encoding="utf-8") as f:
        for rec in chars:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    syllables = set()
    for rec in chars:
        for rd in rec["readings"]:
            syllables |= S.initial_law_variants(rd["reading"])
    syllables = sorted(s for s in syllables if s)
    (S.STAGING / "syllables.txt").write_text("\n".join(syllables) + "\n", encoding="utf-8")

    total_readings = sum(len(r["readings"]) for r in chars)
    S.log(f"wrote staging/characters.jsonl: {len(chars)} chars, {total_readings} readings")
    S.log(f"wrote staging/syllables.txt: {len(syllables)} scrape syllables "
          f"(incl. 두음법칙 variants)")


if __name__ == "__main__":
    main()
