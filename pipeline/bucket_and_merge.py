"""Stage 5 — bucket compounds per character and merge stdict + krdict.

    python -m pipeline.bucket_and_merge --scope core

Reads the staged entries, decomposes each compound's Hanja chain, keeps only
compounds that contain at least one in-scope character, merges stdict (Korean
definitions, the long tail) with krdict (English translations, the curated
core) on (normalized word, Hanja chain), and emits:

  staging/compounds.jsonl            — one row per unique compound
  staging/character_compounds.jsonl  — char↔compound edges with position
  staging/orphan_chars.json          — Hanja seen in compounds but not in the
                                       master list (candidates for backfill)
"""

import argparse
import json
from collections import Counter

from . import sources as S

# stdict POS tags that don't aid Hanja study (verb endings, particles).
DROP_POS = {"어미", "조사"}


def load_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def best_english(senses):
    """Return (english_gloss, english_definition) from the first sense carrying an
    English translation, else (None, None)."""
    for sense in senses:
        for tr in sense.get("translations", []):
            if tr.get("trans_lang") == "영어" and (tr.get("trans_word") or tr.get("trans_dfn")):
                return tr.get("trans_word") or None, tr.get("trans_dfn") or None
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=["core", "full"], default="core")
    args = ap.parse_args()

    chars = load_jsonl(S.STAGING / "characters.jsonl")
    master = {c["hanja"] for c in chars}
    S.log(f"master character set: {len(master)} (scope={args.scope})")

    # compound keyed by (norm_word, hanja_canonical)
    compounds = {}
    orphans = Counter()

    def get_or_make(word_norm, hanja_chain, display_form):
        key = (word_norm, "".join(hanja_chain))
        rec = compounds.get(key)
        if rec is None:
            rec = {
                "word_ko": word_norm,
                "word_ko_raw": None,
                "hanja_form": display_form,
                "hanja_chain": hanja_chain,
                "pos": None,
                "definition_ko": None,
                "definition_en": None,
                "english_gloss": None,
                "stdict_word_no": None,
                "krdict_target_code": None,
            }
            compounds[key] = rec
        return rec

    def note_orphans(hanja_chain):
        for h in hanja_chain:
            if h not in master:
                orphans[h] += 1

    # ── stdict: Korean definitions, the long tail ─────────────────────
    stdict = load_jsonl(S.STAGING / "stdict_entries.jsonl")
    n_std = 0
    for e in stdict:
        if e.get("pos") in DROP_POS:
            continue
        chain = S.hanja_chars(e.get("hanja_raw"))
        if not chain or not any(h in master for h in chain):
            continue
        note_orphans(chain)
        word_norm = S.norm_word(e.get("word"))
        if not word_norm:
            continue
        display = S.nfc(e.get("hanja_raw") or "")
        rec = get_or_make(word_norm, chain, display)
        if rec["word_ko_raw"] is None:
            rec["word_ko_raw"] = e.get("word")
        if rec["definition_ko"] is None and e.get("definition_ko"):
            rec["definition_ko"] = e.get("definition_ko")
        if rec["pos"] is None and e.get("pos"):
            rec["pos"] = e.get("pos")
        if rec["stdict_word_no"] is None:
            rec["stdict_word_no"] = e.get("word_no")
        n_std += 1

    # ── krdict: English translations, the curated core ────────────────
    krdict = load_jsonl(S.STAGING / "krdict_entries.jsonl")
    n_kr = 0
    for e in krdict:
        chain = S.hanja_chars(e.get("origin"))
        if not chain or not any(h in master for h in chain):
            continue
        note_orphans(chain)
        word_norm = S.norm_word(e.get("word"))
        if not word_norm:
            continue
        display = S.nfc(e.get("origin") or "")
        rec = get_or_make(word_norm, chain, display)
        if rec["word_ko_raw"] is None:
            rec["word_ko_raw"] = e.get("word")
        gloss, en_def = best_english(e.get("senses", []))
        if rec["english_gloss"] is None and gloss:
            rec["english_gloss"] = gloss
        if rec["definition_en"] is None and en_def:
            rec["definition_en"] = en_def
        if rec["definition_ko"] is None:
            for sense in e.get("senses", []):
                if sense.get("definition"):
                    rec["definition_ko"] = sense["definition"]
                    break
        if rec["pos"] is None and e.get("pos"):
            rec["pos"] = e.get("pos")
        if rec["krdict_target_code"] is None:
            rec["krdict_target_code"] = e.get("target_code")
        n_kr += 1

    # ── Assign stable ids and emit ────────────────────────────────────
    ordered = sorted(compounds.values(),
                     key=lambda r: ("".join(r["hanja_chain"]), r["word_ko"]))
    with open(S.STAGING / "compounds.jsonl", "w", encoding="utf-8") as f_c, \
         open(S.STAGING / "character_compounds.jsonl", "w", encoding="utf-8") as f_e:
        edge_count = 0
        for cid, rec in enumerate(ordered, 1):
            rec["id"] = cid
            rec["has_english"] = 1 if rec["definition_en"] or rec["english_gloss"] else 0
            f_c.write(json.dumps(rec, ensure_ascii=False) + "\n")
            for pos, h in enumerate(rec["hanja_chain"]):
                if h in master:
                    f_e.write(json.dumps(
                        {"hanja": h, "compound_id": cid, "position": pos},
                        ensure_ascii=False) + "\n")
                    edge_count += 1

    (S.STAGING / "orphan_chars.json").write_text(
        json.dumps(dict(orphans.most_common()), ensure_ascii=False, indent=2),
        encoding="utf-8")

    with_en = sum(1 for r in ordered if r["has_english"])
    S.log(f"stdict contributed {n_std} entries, krdict {n_kr}")
    S.log(f"compounds: {len(ordered)} unique | with English: {with_en} "
          f"({100 * with_en // max(len(ordered), 1)}%)")
    S.log(f"character_compounds edges: {edge_count}")
    S.log(f"orphan Hanja (in compounds, not in master): {len(orphans)} distinct")


if __name__ == "__main__":
    main()
