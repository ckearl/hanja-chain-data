"""Stage 3 — scrape 표준국어대사전 by syllable (resume-safe).

    python -m pipeline.scrape_stdict --scope core            # all syllables
    python -m pipeline.scrape_stdict --scope core --syllable 학   # smoke test
    python -m pipeline.scrape_stdict --syllable 학 --max-pages 2  # tiny smoke

Resume model (so the multi-hour run can be killed/restarted, and the rycont
expansion reuses the core scrape for free):
  - raw/stdict/{syllable}_p{N}.html  — cached page; if present we read instead of
    re-fetching (no network, no delay).
  - staging/stdict/{syllable}.jsonl  — per-syllable parsed entries; a syllable
    with this file is considered done and skipped unless --force.
  - staging/stdict_entries.jsonl     — consolidated concat of all per-syllable
    files, rebuilt at the end of every run.
"""

import argparse
import json
import time

from . import sources as S

STDICT_RAW = S.RAW / "stdict"
STDICT_STAGE = S.STAGING / "stdict"


def scrape_syllable(syllable, max_pages=None, label=""):
    """Fetch (or read cached) all pages for *{syllable}*; return parsed entries.

    Logs a start line (with total + page count) and a heartbeat every 25 pages,
    so high-frequency syllables (가 ~185 pages, 사 ~387) show progress instead of
    appearing frozen while they grind through hundreds of pages."""
    wildcarded = S.STDICT_WILDCARD.format(kw=syllable)
    entries = []
    total = None
    last_page = None  # computed from total once known
    page = 1
    started = time.time()
    complete = False  # True only when we stop on a real end-of-results condition
    while True:
        raw_path = STDICT_RAW / f"{syllable}_p{page}.html"
        if raw_path.exists():
            html = raw_path.read_text(encoding="utf-8")
            fetched = False
        else:
            html = _fetch_with_retry(wildcarded, page, label, syllable)
            if html is None:  # network died (e.g. wake-from-sleep) — leave the
                break          # syllable INCOMPLETE so it resumes on rerun
            raw_path.write_text(html, encoding="utf-8")
            fetched = True

        if total is None:
            total = S.parse_total(html)
            if total:
                last_page = -(-total // S.STDICT_PAGE_SIZE)  # ceil
            S.log(f"  {label}{syllable}: total {total} -> ~{last_page or '?'} pages")

        page_entries = S.parse_stdict_html(html)
        for e in page_entries:
            e["syllable"] = syllable
        entries.extend(page_entries)

        # Stop conditions. We drive pagination by the reported total rather than
        # the paging widget: stdict's widget shows only a sliding window of page
        # numbers (at page 50 it lists 1-50, hiding 51-96), so has_more_pages
        # would falsely stop us early on high-frequency syllables.
        if not page_entries:
            complete = True
            break
        if total and len(entries) >= total:
            complete = True
            break
        if last_page is not None:
            if page >= last_page:
                complete = True
                break
        elif not S.has_more_pages(html, page):  # no total -> fall back to widget
            complete = True
            break
        if max_pages and page >= max_pages:
            complete = True  # intentional cap counts as a clean stop
            break
        if page % 25 == 0:
            S.log(f"  {label}{syllable}: page {page}/{last_page or '?'} "
                  f"({len(entries)} entries, {time.time() - started:.0f}s)")
        page += 1
        if fetched:
            time.sleep(S.DELAY)
    return entries, total or len(entries), complete


def _fetch_with_retry(wildcarded, page, label, syllable, tries=3):
    """POST a page, retrying transient failures with backoff. Returns the HTML,
    or None if all attempts fail (signals the caller to stop incomplete)."""
    for attempt in range(1, tries + 1):
        try:
            return S.stdict_post(wildcarded, page)
        except Exception as e:
            S.log(f"  {label}{syllable}: p{page} error (try {attempt}/{tries}): {e}")
            if attempt < tries:
                time.sleep(2 * attempt)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=["core", "full"], default="core")
    ap.add_argument("--syllable", help="scrape only this one syllable (smoke test)")
    ap.add_argument("--max-pages", type=int, default=None,
                    help="cap pages per syllable (smoke test only)")
    ap.add_argument("--force", action="store_true",
                    help="re-parse syllables even if their staging file exists")
    args = ap.parse_args()
    S.ensure_dirs()
    STDICT_STAGE.mkdir(parents=True, exist_ok=True)

    if args.syllable:
        syllables = [S.nfc(args.syllable)]
    else:
        syllables = [s for s in (S.STAGING / "syllables.txt").read_text(
            encoding="utf-8").split("\n") if s]

    done = sum(1 for syl in syllables if (STDICT_STAGE / f"{syl}.jsonl").exists())
    S.log(f"stdict scrape: {len(syllables)} syllable(s), scope={args.scope} "
          f"({done} already done, {len(syllables) - done} to go)")
    for i, syl in enumerate(syllables, 1):
        stage_path = STDICT_STAGE / f"{syl}.jsonl"
        if stage_path.exists() and not args.force:
            continue
        label = f"[{i}/{len(syllables)}] "
        entries, total, complete = scrape_syllable(syl, max_pages=args.max_pages, label=label)
        if not complete:
            # Don't finalize a truncated syllable: leave its staging file unwritten
            # so the next run resumes it (cached pages persist and are reused).
            S.log(f"  {label}{syl}: INTERRUPTED at {len(entries)} entries — not "
                  f"finalized; rerun to resume. Stopping (likely network down).")
            break
        with open(stage_path, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        S.log(f"  {label}{syl}: DONE {len(entries)} entries "
              f"(reported total {total})")

    # Consolidate every per-syllable file into one entries stream.
    n = 0
    with open(S.STAGING / "stdict_entries.jsonl", "w", encoding="utf-8") as out:
        for path in sorted(STDICT_STAGE.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    out.write(line + "\n")
                    n += 1
    S.log(f"consolidated staging/stdict_entries.jsonl: {n} entries "
          f"from {len(list(STDICT_STAGE.glob('*.jsonl')))} syllables")


if __name__ == "__main__":
    main()
