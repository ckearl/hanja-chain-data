"""Stage 4 — fetch krdict (한국어기초사전) by syllable.

    python -m pipeline.scrape_krdict --scope core
    python -m pipeline.scrape_krdict --syllable 학   # smoke test

One GET per syllable (num=100). The API effectively caps each query at 100
results regardless of the reported total — an accepted limit given the
"krdict only, partial English" scope. Resume-safe via cached raw XML.
"""

import argparse
import json
import time

from . import sources as S

KRDICT_RAW = S.RAW / "krdict"
KRDICT_STAGE = S.STAGING / "krdict"


def scrape_syllable(syllable):
    raw_path = KRDICT_RAW / f"{syllable}.xml"
    if raw_path.exists():
        xml_text = raw_path.read_text(encoding="utf-8")
        fetched = False
    else:
        xml_text = S.krdict_call(syllable)
        raw_path.write_text(xml_text, encoding="utf-8")
        fetched = True
    total, entries = S.parse_krdict_xml(xml_text)
    for e in entries:
        e["syllable"] = syllable
    return entries, total, fetched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=["core", "full"], default="core")
    ap.add_argument("--syllable", help="scrape only this one syllable (smoke test)")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    S.ensure_dirs()
    KRDICT_STAGE.mkdir(parents=True, exist_ok=True)

    if not S.KRDICT_API_KEY:
        S.log("ERROR: KRDICT_API_KEY env var not set; aborting.")
        raise SystemExit(1)

    if args.syllable:
        syllables = [S.nfc(args.syllable)]
    else:
        syllables = [s for s in (S.STAGING / "syllables.txt").read_text(
            encoding="utf-8").split("\n") if s]

    S.log(f"krdict scrape: {len(syllables)} syllable(s), scope={args.scope}")
    for i, syl in enumerate(syllables, 1):
        stage_path = KRDICT_STAGE / f"{syl}.jsonl"
        if stage_path.exists() and not args.force:
            continue
        entries, total, fetched = scrape_syllable(syl)
        with open(stage_path, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        capped = " (CAPPED at 100)" if total > S.KRDICT_NUM else ""
        S.log(f"  [{i}/{len(syllables)}] {syl}: {len(entries)} of {total}{capped}")
        if fetched:
            time.sleep(S.DELAY)

    n = 0
    with open(S.STAGING / "krdict_entries.jsonl", "w", encoding="utf-8") as out:
        for path in sorted(KRDICT_STAGE.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    out.write(line + "\n")
                    n += 1
    S.log(f"consolidated staging/krdict_entries.jsonl: {n} entries")


if __name__ == "__main__":
    main()
