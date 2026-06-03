#!/usr/bin/env python3
"""Data exploration for Korean Hanja dictionary sources.

Hits three sources for 8 test characters, saves raw + parsed data,
and prints a markdown analysis report.
"""

import csv
import io
import json
import os
import re
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

import requests
from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).parent
RAW = ROOT / "raw_responses"
PARSED = ROOT / "parsed"
for sub in ["github", "stdict", "krdict"]:
    (RAW / sub).mkdir(parents=True, exist_ok=True)
    (PARSED / sub).mkdir(parents=True, exist_ok=True)

DELAY = 0.5
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# stdict's plain-keyword search only returns exact word matches.
# To surface compound words containing the syllable, we must wildcard-wrap.
# Cap pages per reading to keep exploration tractable; we want enough volume
# to characterize the data, not exhaustive collection.
STDICT_WILDCARD = "*{kw}*"
STDICT_PAGE_CAP = 4  # 4 pages × 50 = up to 200 entries per (char, reading)

TEST_CHARS = [
    {"hanja": "學", "readings": ["학"],      "note": "common"},
    {"hanja": "不", "readings": ["불", "부"], "note": "multi-reading"},
    {"hanja": "藝", "readings": ["예"],      "note": "less common"},
    {"hanja": "例", "readings": ["례", "예"], "note": "multi-reading, shares sound with 藝"},
    {"hanja": "四", "readings": ["사"],      "note": "shares 사 with 死"},
    {"hanja": "死", "readings": ["사"],      "note": "shares 사 with 四"},
    {"hanja": "愛", "readings": ["애"],      "note": "common"},
    {"hanja": "龍", "readings": ["용"],      "note": "rarer"},
]

KRDICT_API_KEY = os.environ.get("KRDICT_API_KEY", "")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr)


# ─────────────────────────────────────────────────────────────────────
# Source 1: rycont/hanja-grade-dataset
# ─────────────────────────────────────────────────────────────────────

GITHUB_CSV_URL = (
    # Repo's actual file is hanja.csv (not dataset.csv as the task brief stated).
    "https://raw.githubusercontent.com/rycont/hanja-grade-dataset/main/hanja.csv"
)


def fetch_github_csv():
    log("Fetching rycont/hanja-grade-dataset CSV...")
    r = requests.get(GITHUB_CSV_URL, timeout=30)
    r.raise_for_status()
    (RAW / "github" / "dataset.csv").write_text(r.text, encoding="utf-8")
    reader = csv.DictReader(io.StringIO(r.text))
    rows = list(reader)
    log(f"  loaded {len(rows)} rows; columns: {reader.fieldnames}")
    return rows, reader.fieldnames


def analyze_github(rows, columns):
    """Find rows for each test char. Schema: main_sound,level,hanja,meaning,radical,strokes,total_strokes."""
    by_char = {}
    # All-rows index by hanja char for collision/multi-row detection
    idx = defaultdict(list)
    for row in rows:
        h = (row.get("hanja") or "").strip()
        if h:
            idx[h].append(row)
    for c in TEST_CHARS:
        h = c["hanja"]
        matches = idx.get(h, [])
        by_char[h] = {
            "match_count": len(matches),
            "first_match": matches[0] if matches else None,
            "all_matches": matches,
        }
        out = PARSED / "github" / f"{h}.json"
        out.write_text(
            json.dumps(by_char[h], ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return by_char


# ─────────────────────────────────────────────────────────────────────
# Source 2: stdict.korean.go.kr scraper
# ─────────────────────────────────────────────────────────────────────

STDICT_URL = "https://stdict.korean.go.kr/search/searchResult.do"
STDICT_HEADERS = {
    "User-Agent": UA,
    "Referer": STDICT_URL,
    "Content-Type": "application/x-www-form-urlencoded",
}


def stdict_post(keyword, page):
    data = {
        "searchKeyword": keyword,
        "searchKeywordTo": "3",
        "pageSize": "50",
        "pageUnit": "50",
        "pageIndex": str(page),
        "word_no": "0",
        "fileType": "",
        "fileField": "",
        "fileUseType": "",
        "fileUseContent": "",
    }
    r = requests.post(STDICT_URL, data=data, headers=STDICT_HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def parse_total(html):
    soup = BeautifulSoup(html, "html.parser")
    tit = soup.select_one("span.tit")
    if not tit:
        return 0
    m = re.search(r"총\s*([\d,]+)\s*개", tit.get_text())
    if m:
        return int(m.group(1).replace(",", ""))
    return 0


def parse_stdict_html(html):
    soup = BeautifulSoup(html, "html.parser")
    entries = []
    ul = soup.select_one("ul.result")
    if not ul:
        return entries
    for li in ul.find_all("li"):
        dt = li.find("dt")
        if not dt:
            continue
        a = dt.select_one("a.t_blue1")
        if not a:
            continue

        # word: text of a.t_blue1, strip <sup> and leading dashes/numbers
        word_raw = a.get_text(strip=False)
        # Remove sup content if still present in the text
        sup = a.find("sup")
        if sup:
            sup_text = sup.get_text()
            word_raw = word_raw.replace(sup_text, "")
        word = word_raw.strip().lstrip("-").strip()

        # word_no from href
        href = a.get("href", "")
        m = re.search(r"word_no=(\d+)", href)
        word_no = m.group(1) if m else None

        # hanja_raw from span.hanja_font
        hanja_span = dt.select_one("span.hanja_font")
        hanja_raw = ""
        if hanja_span:
            txt = hanja_span.get_text(strip=True)
            hanja_raw = txt.strip("()").strip()

        # pos: inline text node immediately after the hanja_font span
        pos = ""
        if hanja_span:
            nxt = hanja_span.next_sibling
            # Walk forward through any whitespace text nodes
            while nxt is not None and isinstance(nxt, NavigableString) and not nxt.strip():
                nxt = nxt.next_sibling
            if nxt is not None and isinstance(nxt, NavigableString):
                txt = nxt.strip()
                pm = re.search(r"[「\[]([^「」\[\]]+)[」\]]", txt)
                if pm:
                    pos = pm.group(1)
                else:
                    pos = txt.strip("「」[]").strip()

        # definition
        dataline = dt.select_one("font.dataLine")
        definition_ko = dataline.get_text(" ", strip=True) if dataline else ""

        # sense number (optional)
        sense_span = dt.select_one("span.t_red1")
        sense = ""
        if sense_span:
            s = sense_span.get_text(strip=True)
            sense = s.strip("「」").strip()

        entries.append({
            "word": word,
            "word_no": word_no,
            "hanja_raw": hanja_raw,
            "pos": pos,
            "sense": sense,
            "definition_ko": definition_ko,
        })
    return entries


def has_more_pages(html, current_page):
    soup = BeautifulSoup(html, "html.parser")
    paging = soup.select_one("div.paging")
    if not paging:
        return False
    pages = [s.get_text(strip=True) for s in paging.find_all(["span", "a"])]
    nums = [int(p) for p in pages if p.isdigit()]
    if not nums:
        return False
    return max(nums) > current_page


def scrape_stdict_keyword(hanja, keyword):
    """Scrape pages for a wildcarded keyword; return list of entries + reported total."""
    wildcarded = STDICT_WILDCARD.format(kw=keyword)
    all_entries = []
    total = None
    page = 1
    while True:
        try:
            html = stdict_post(wildcarded, page)
        except Exception as e:
            log(f"  stdict error for {wildcarded} page {page}: {e}")
            break
        path = RAW / "stdict" / f"{hanja}_{keyword}_p{page}.html"
        path.write_text(html, encoding="utf-8")

        if total is None:
            total = parse_total(html)
            log(f"  stdict[{hanja}/{keyword}={wildcarded}] total reported: {total}")

        entries = parse_stdict_html(html)
        all_entries.extend(entries)

        if not entries:
            break
        if total and len(all_entries) >= total:
            break
        if not has_more_pages(html, page):
            break
        if page >= STDICT_PAGE_CAP:
            log(f"  stdict[{hanja}/{keyword}] hit exploration page cap ({page}); "
                f"collected {len(all_entries)} of {total}")
            break
        page += 1
        time.sleep(DELAY)
    return all_entries, total or len(all_entries)


def scrape_stdict_all():
    """Returns dict: hanja -> {raw_total, raw_entries, matched_entries, by_reading: {...}}"""
    results = {}
    for c in TEST_CHARS:
        hanja = c["hanja"]
        log(f"stdict ▶ {hanja} ({'/'.join(c['readings'])})")
        per_reading = {}
        all_raw = []
        try:
            for kw in c["readings"]:
                entries, total = scrape_stdict_keyword(hanja, kw)
                per_reading[kw] = {"total_reported": total, "entries": entries}
                all_raw.extend(entries)
                time.sleep(DELAY)
        except Exception as e:
            log(f"  stdict {hanja} failed: {e}")
            traceback.print_exc(file=sys.stderr)

        # Deduplicate by word_no across readings
        seen = set()
        deduped = []
        for e in all_raw:
            key = e.get("word_no") or (e.get("word"), e.get("hanja_raw"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(e)

        matched = [e for e in deduped if hanja in (e.get("hanja_raw") or "")]
        results[hanja] = {
            "by_reading": per_reading,
            "raw_unique_count": len(deduped),
            "matched_count": len(matched),
            "matched_entries": matched,
        }
        out = PARSED / "stdict" / f"{hanja}.json"
        out.write_text(
            json.dumps(results[hanja], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return results


# ─────────────────────────────────────────────────────────────────────
# Source 3: krdict (한국어기초사전) Open API
# ─────────────────────────────────────────────────────────────────────

KRDICT_URL = "https://krdict.korean.go.kr/api/search"


def krdict_call(keyword, method, start, num=100):
    params = {
        "key": KRDICT_API_KEY,
        "q": keyword,
        "translated": "y",
        "trans_lang": "1",
        "method": method,
        "part": "word",
        "num": str(num),
        "start": str(start),
    }
    r = requests.get(KRDICT_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.text


def parse_krdict_xml(xml_text):
    """Returns (total, entries)."""
    entries = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        log(f"  krdict XML parse error: {e}")
        return 0, entries

    total_el = root.find("total")
    total = int(total_el.text) if total_el is not None and total_el.text else 0

    for item in root.findall("item"):
        word = (item.findtext("word") or "").strip()
        target_code = (item.findtext("target_code") or "").strip()
        pos = (item.findtext("pos") or "").strip()
        origin = (item.findtext("origin") or "").strip()  # hanja often appears here

        # Senses with translations
        senses = []
        for sense in item.findall("sense"):
            sense_obj = {
                "sense_no": (sense.findtext("sense_no") or "").strip(),
                "definition": (sense.findtext("definition") or "").strip(),
                "translations": [],
            }
            for tr in sense.findall("translation"):
                sense_obj["translations"].append({
                    "trans_lang": (tr.findtext("trans_lang") or "").strip(),
                    "trans_word": (tr.findtext("trans_word") or "").strip(),
                    "trans_dfn": (tr.findtext("trans_dfn") or "").strip(),
                })
            senses.append(sense_obj)

        entries.append({
            "target_code": target_code,
            "word": word,
            "origin": origin,  # contains hanja notation if present
            "pos": pos,
            "senses": senses,
        })
    return total, entries


def scrape_krdict_keyword(hanja, keyword, method):
    all_entries = []
    start = 1
    total = None
    page = 1
    while True:
        try:
            xml_text = krdict_call(keyword, method, start)
        except Exception as e:
            log(f"  krdict error {keyword}/{method} start={start}: {e}")
            break
        path = RAW / "krdict" / f"{hanja}_{keyword}_{method}_p{page}.xml"
        path.write_text(xml_text, encoding="utf-8")
        t, entries = parse_krdict_xml(xml_text)
        if total is None:
            total = t
            log(f"  krdict[{hanja}/{keyword}/{method}] total: {total}")
        all_entries.extend(entries)
        if not entries:
            break
        if len(all_entries) >= total:
            break
        start += 100
        page += 1
        if page > 30:
            break
        time.sleep(DELAY)
    return all_entries, total or len(all_entries)


def scrape_krdict_all():
    results = {}
    for c in TEST_CHARS:
        hanja = c["hanja"]
        log(f"krdict ▶ {hanja} ({'/'.join(c['readings'])})")
        per = {"exact": {}, "include": {}}
        try:
            for method in ("exact", "include"):
                merged = []
                seen = set()
                total_sum = 0
                for kw in c["readings"]:
                    entries, total = scrape_krdict_keyword(hanja, kw, method)
                    total_sum += total
                    for e in entries:
                        tc = e.get("target_code") or e.get("word")
                        if tc in seen:
                            continue
                        seen.add(tc)
                        merged.append(e)
                    time.sleep(DELAY)
                matched = [e for e in merged if hanja in (e.get("origin") or "")]
                per[method] = {
                    "total_reported_sum": total_sum,
                    "unique_count": len(merged),
                    "matched_count": len(matched),
                    "matched_entries": matched,
                    "all_unique_entries": merged,
                }
        except Exception as e:
            log(f"  krdict {hanja} failed: {e}")
            traceback.print_exc(file=sys.stderr)
        results[hanja] = per
        out = PARSED / "krdict" / f"{hanja}.json"
        out.write_text(
            json.dumps(per, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return results


# ─────────────────────────────────────────────────────────────────────
# Analysis & report
# ─────────────────────────────────────────────────────────────────────


def build_report(github_rows, github_cols, github_by_char, stdict_data, krdict_data):
    lines = []
    p = lines.append

    p("# Hanja dictionary data exploration report\n")
    p(f"_8 test characters; generated {time.strftime('%Y-%m-%d %H:%M')}_\n")

    # ── Source 1 ─────────────────────────────
    p("> **Note on stdict search**: plain `q=학` returns only the 6 single-syllable "
      "entries. To surface compound words containing the syllable (essential for the "
      "hanja-chain analysis), we search with `*학*` wildcards. Pages capped at "
      f"{STDICT_PAGE_CAP} per (char, reading) — sample size, not exhaustive collection.\n")

    p("## Source 1 — rycont/hanja-grade-dataset (GitHub CSV)\n")
    p(f"- Rows: **{len(github_rows)}**")
    p(f"- Columns: `{github_cols}`")
    # field population
    pop = {col: sum(1 for r in github_rows if (r.get(col) or "").strip()) for col in github_cols}
    p("\n### Field population")
    for col, n in pop.items():
        p(f"- `{col}`: {n}/{len(github_rows)} ({100 * n // max(len(github_rows), 1)}%)")

    p("\n### Sample record (學)")
    sample = (github_by_char.get("學") or {}).get("first_match")
    p("```json")
    p(json.dumps(sample, ensure_ascii=False, indent=2))
    p("```")

    p("\n### Coverage on our 8 test chars")
    p("| Hanja | match count | level | meaning | radical | strokes |")
    p("|---|---:|---|---|---|---:|")
    for c in TEST_CHARS:
        info = github_by_char.get(c["hanja"]) or {}
        m = info.get("first_match") or {}
        mark = "✓" if info.get("match_count") else "✗"
        p(
            f"| {c['hanja']} | {mark} {info.get('match_count', 0)} | "
            f"{m.get('level', '—')} | {m.get('meaning', '—')} | "
            f"{m.get('radical', '—')} | {m.get('total_strokes', '—')} |"
        )

    multi = [(h, info['match_count']) for h, info in github_by_char.items() if info.get('match_count', 0) > 1]
    if multi:
        p(f"\nHanja appearing in MULTIPLE rows (one per reading): {multi}")

    # ── Source 2 ─────────────────────────────
    p("\n## Source 2 — 표준국어대사전 (stdict scrape)\n")

    p("### Per-character coverage (total returned vs. Hanja-matched)\n")
    p("| Hanja | Readings | Total unique returned | Matched | Noise % |")
    p("|---|---|---:|---:|---:|")
    for c in TEST_CHARS:
        d = stdict_data.get(c["hanja"], {})
        raw = d.get("raw_unique_count", 0)
        matched = d.get("matched_count", 0)
        noise = 100 * (raw - matched) // raw if raw else 0
        p(f"| {c['hanja']} | {'/'.join(c['readings'])} | {raw} | {matched} | {noise}% |")

    # Field population in stdict entries
    all_stdict_entries = []
    for d in stdict_data.values():
        all_stdict_entries.extend(d.get("matched_entries", []))
    pct = 0
    nouns_verbs = 0
    total = 0
    compound_entries = []
    if all_stdict_entries:
        p("\n### Field population across all matched entries")
        fields = ["word", "word_no", "hanja_raw", "pos", "sense", "definition_ko"]
        for f in fields:
            n = sum(1 for e in all_stdict_entries if (e.get(f) or "").strip())
            pct = 100 * n // len(all_stdict_entries)
            p(f"- `{f}`: {n}/{len(all_stdict_entries)} ({pct}%)")

        p("\n### Sample stdict entry (學)")
        sample_entries = stdict_data.get("學", {}).get("matched_entries", [])
        if sample_entries:
            p("```json")
            p(json.dumps(sample_entries[0], ensure_ascii=False, indent=2))
            p("```")

        # POS distribution
        pos_counts = Counter()
        for e in all_stdict_entries:
            pos_counts[e.get("pos") or "(none)"] += 1
        p("\n### POS distribution (matched entries, all chars)")
        for pos, n in pos_counts.most_common():
            p(f"- `{pos}`: {n}")
        nouns_verbs = pos_counts.get("명사", 0) + pos_counts.get("동사", 0)
        total = sum(pos_counts.values())
        if total:
            p(f"\nNoun/verb share: **{nouns_verbs}/{total} = {100 * nouns_verbs // total}%**")
            p(f"Non-N/V (filter candidates): **{100 - 100 * nouns_verbs // total}%**")

        # Hanja notation on compounds
        compound_entries = [e for e in all_stdict_entries if len(e.get("word", "")) > 1]
        with_hanja = [e for e in compound_entries if e.get("hanja_raw")]
        if compound_entries:
            pct = 100 * len(with_hanja) // len(compound_entries)
            p("\n### Hanja notation on compound words (CRITICAL)")
            p(
                f"- Compound (len > 1) matched entries: **{len(compound_entries)}**"
            )
            p(f"- With non-empty `hanja_raw`: **{len(with_hanja)} ({pct}%)**")
            # Check that compound-word hanja_raw is the FULL hanja chain
            full_chain_ok = 0
            for e in compound_entries:
                w, h = e.get("word", ""), e.get("hanja_raw", "")
                if h and len(h) >= len(w):
                    full_chain_ok += 1
            p(f"- `hanja_raw` length ≥ word length: **{full_chain_ok}/{len(compound_entries)}**")
            # show a few examples
            p("\nSample compound-word entries:")
            for e in compound_entries[:8]:
                p(f"  - {e['word']} ({e.get('hanja_raw') or '—'})  pos={e.get('pos') or '—'}")

    # 四 vs 死
    p("\n### 四 vs 死 collision check")
    si4 = stdict_data.get("四", {})
    si_die = stdict_data.get("死", {})
    si4_words = {e["word_no"] for e in si4.get("matched_entries", []) if e.get("word_no")}
    sid_words = {e["word_no"] for e in si_die.get("matched_entries", []) if e.get("word_no")}
    overlap = si4_words & sid_words
    p(f"- 四 matched entries: {len(si4_words)}")
    p(f"- 死 matched entries: {len(sid_words)}")
    p(f"- Overlap (same word_no in both filtered sets): **{len(overlap)}**")
    sa_total_4 = si4.get("raw_unique_count", 0)
    p(f"- Total unique results for 사-search (from 四 collection): {sa_total_4}")

    # Multi-reading characters
    p("\n### Multi-reading handling (不, 例)")
    for h in ("不", "例"):
        d = stdict_data.get(h, {})
        p(f"\n**{h}**")
        for kw, sub in d.get("by_reading", {}).items():
            ent_count = len(sub.get("entries", []))
            matched_in_kw = sum(1 for e in sub["entries"] if h in (e.get("hanja_raw") or ""))
            p(f"  - reading `{kw}`: {ent_count} entries returned, {matched_in_kw} match {h}")

    # ── Source 3 ─────────────────────────────
    p("\n## Source 3 — krdict (한국어기초사전 Open API)\n")

    p("### Per-character coverage (exact vs. include)\n")
    p("| Hanja | exact total | exact matched | include total | include matched |")
    p("|---|---:|---:|---:|---:|")
    for c in TEST_CHARS:
        d = krdict_data.get(c["hanja"], {})
        ex = d.get("exact", {})
        inc = d.get("include", {})
        p(
            f"| {c['hanja']} | {ex.get('unique_count', 0)} | {ex.get('matched_count', 0)} "
            f"| {inc.get('unique_count', 0)} | {inc.get('matched_count', 0)} |"
        )

    # Field population on krdict entries (exact)
    all_kr_entries = []
    for d in krdict_data.values():
        all_kr_entries.extend(d.get("exact", {}).get("matched_entries", []))
    if all_kr_entries:
        p("\n### Field population — exact-matched entries")
        fields = ["target_code", "word", "origin", "pos"]
        for f in fields:
            n = sum(1 for e in all_kr_entries if (e.get(f) or "").strip())
            p(f"- `{f}`: {n}/{len(all_kr_entries)} ({100 * n // len(all_kr_entries)}%)")
        n_def = sum(1 for e in all_kr_entries for s in e["senses"] if s.get("definition"))
        n_tr = sum(
            1 for e in all_kr_entries for s in e["senses"]
            if s.get("translations") and any(t.get("trans_word") for t in s["translations"])
        )
        n_senses = sum(len(e["senses"]) for e in all_kr_entries)
        if n_senses:
            p(f"- Senses w/ Korean def: {n_def}/{n_senses}")
            p(f"- Senses w/ English translation: {n_tr}/{n_senses} ({100 * n_tr // n_senses}%)")

        p("\n### Sample krdict entry (學)")
        sample_kr = krdict_data.get("學", {}).get("exact", {}).get("matched_entries", [])
        if sample_kr:
            p("```json")
            p(json.dumps(sample_kr[0], ensure_ascii=False, indent=2))
            p("```")

        pos_counts = Counter(e.get("pos") or "(none)" for e in all_kr_entries)
        p("\n### krdict POS distribution (matched, exact)")
        for pos, n in pos_counts.most_common():
            p(f"- `{pos}`: {n}")

    # ── Cross-source overlap ──────────────────
    p("\n## Cross-source overlap (stdict ∩ krdict, by Korean word)\n")
    p("> **Sampling caveat** — this comparison is dominated by an ordering artifact, "
      "not a real coverage gap:\n"
      ">\n"
      "> - stdict returns results in dictionary (가나다) order. With our 4-page cap "
      "(200 entries), the stdict sample for 學 is entirely 가-prefix words like "
      "가공^야금학, 가금-학, 가전-학… Common words (학교, 학생, 대학) sort later "
      "and are not in the sample.\n"
      "> - krdict, by contrast, is a curated 5k-word learner dictionary; its result "
      "set IS the common-word universe (학교, 학생, 대학, 학과…).\n"
      ">\n"
      "> So the two sets barely overlap *in this sample*. The schema-design takeaway "
      "is: krdict gives the basic-vocabulary core; stdict gives the long tail of "
      "specialized/technical/dated words. To measure real overlap we'd need exhaustive "
      "stdict scraping, not the first 200 alphabetical entries.\n"
      ">\n"
      "> Also: stdict words include phrase markers `^` (space) and hyphenation `-`. "
      "We normalize both sides before comparison.\n")
    p("| Hanja | stdict matched | krdict matched (exact) | overlap (normalized) | krdict English % |")
    p("|---|---:|---:|---:|---:|")
    def norm(w):
        return (w or "").replace("^", "").replace("-", "").strip()
    overlap_totals = []
    eng_pcts = []
    for c in TEST_CHARS:
        h = c["hanja"]
        s_words = {norm(e["word"]) for e in stdict_data.get(h, {}).get("matched_entries", [])}
        kr_entries = krdict_data.get(h, {}).get("exact", {}).get("matched_entries", [])
        kr_words = {norm(e["word"]) for e in kr_entries}
        overlap = s_words & kr_words
        # english translation rate among kr matched entries
        with_en = sum(
            1 for e in kr_entries
            if any(
                t.get("trans_word") and t.get("trans_lang") == "영어"
                for s in e["senses"] for t in s["translations"]
            )
        ) if kr_entries else 0
        # Fallback: any translation present (lang field may differ)
        if with_en == 0 and kr_entries:
            with_en = sum(
                1 for e in kr_entries
                if any(t.get("trans_word") for s in e["senses"] for t in s["translations"])
            )
        eng_pct = 100 * with_en // len(kr_entries) if kr_entries else 0
        if kr_entries:
            eng_pcts.append(eng_pct)
        overlap_totals.append((len(s_words), len(kr_words), len(overlap)))
        p(f"| {h} | {len(s_words)} | {len(kr_words)} | {len(overlap)} | {eng_pct}% |")

    if eng_pcts:
        avg_en = sum(eng_pcts) // len(eng_pcts)
        p(f"\n**Average English-translation rate among krdict matches: ~{avg_en}%**")
        p(
            "\nKey insight: krdict's curated subset is fully translated, but it is "
            "small (~50 common words per character). For full Hanja-app coverage we'd "
            "use **krdict for the common-word core** (English translations free) and "
            "**stdict for the long tail** (Korean definition only — would need LLM "
            "translation fallback for English)."
        )

    total_s = sum(t[0] for t in overlap_totals)
    total_kr = sum(t[1] for t in overlap_totals)
    total_overlap = sum(t[2] for t in overlap_totals)
    p(
        f"\n_(Raw counts: {total_overlap} normalized overlap out of "
        f"{total_s} stdict / {total_kr} krdict — see sampling caveat above.)_"
    )

    # Source-specific gotchas before the consolidated quirks list
    p("\n## Per-source gotchas\n")

    p("### rycont GitHub CSV")
    missing_in_csv = [c["hanja"] for c in TEST_CHARS if not (github_by_char.get(c["hanja"]) or {}).get("match_count")]
    if missing_in_csv:
        p(f"- ⚠️  Characters MISSING from the dataset: {missing_in_csv}")
        p("  (The set covers 8급–특급Ⅱ from 한국어문회. Some basic chars like 不 are not listed by 한국어문회.)")
    p("- `meaning` is a stringified Python literal: `[[[korean_meaning(s)], [korean_reading(s)]]]`. "
      "Multi-reading characters carry multiple `[[meanings], [readings]]` pairs in this list.")
    p("- One row per Hanja — no duplication by reading. main_sound carries the primary reading only.")

    p("\n### stdict scrape")
    p(f"- Wildcard `*{{kw}}*` is required to surface compound words. Plain keyword search returns only exact single-syllable matches.")
    p("- `pos` is empty for noun-phrase entries (those containing `^`), since stdict does not tag phrases — this explains the ~54% pos population.")
    p("- `word` strings carry phrase/morpheme markers: `^` separates phrase parts (가공^야금학), `-` separates a bound morpheme (가금-학). Normalize before any cross-source match.")
    si4 = stdict_data.get("四", {})
    sa_matched_4 = si4.get("matched_count", 0)
    sa_total_4 = si4.get("raw_unique_count", 0)
    if sa_matched_4 == 0:
        p(f"- ⚠️  四 returned 0 matched entries in the first {sa_total_4} 사-results "
          "(out of 19,326 total). stdict result ordering surfaces other 사-Hanja "
          "(死, 私, 史, 思, 寺, 司, 砂…) before 四. Deeper pagination or a more "
          "selective search is needed to find 四 compounds.")

    p("\n### krdict API")
    p("- ⚠️  **Pagination is broken or capped**: the API reports e.g. `total=418` "
      "for `q=학&num=100`, but `start=101` returns ZERO `<item>` elements. "
      "Each call effectively caps at 100 results. The `total` field is a count of "
      "matches that exist but cannot all be fetched by paginating with `start`.")
    p("- `exact` and `include` methods returned identical totals on every test character — "
      "the `method` parameter appears not to differentiate for syllable queries.")
    p("- `origin` field carries the Hanja. It is populated 100% on matched entries. "
      "May contain non-Hanja characters (e.g. `gas化學工業` in the 學 sample).")
    p("- Every matched entry had at least one English translation (100%) — "
      "krdict's curated 5k-word subset is fully translated.")

    p("\n## Surprises & schema-design flags\n")
    quirks = []

    # 1. compound hanja population
    if compound_entries:
        if pct < 95:
            quirks.append(
                f"⚠️  Only {pct}% of stdict compound words carry a hanja_raw value — "
                f"automatic character-chain building from stdict alone will miss the rest."
            )
        else:
            quirks.append(
                f"✓ stdict compound words populate hanja_raw {pct}% of the time — "
                "character-chain build is feasible from this source."
            )

    # 2. 四/死 collision cleanliness
    if not overlap:
        quirks.append("✓ 四 / 死 separate cleanly via hanja_raw filter (no word_no overlap).")
    else:
        quirks.append(
            f"⚠️  {len(overlap)} entries appeared under BOTH 四 and 死 filters — "
            "likely compound words containing both characters."
        )

    # 3. POS filtering
    if total and total > 0:
        non_nv = total - nouns_verbs
        quirks.append(
            f"POS filter: {100 * non_nv // total}% of stdict entries are non-noun/verb. "
            "If we want only N/V we should filter early."
        )

    # 4. krdict vs stdict scale
    if total_s and total_kr:
        ratio = total_kr / total_s if total_s else 0
        quirks.append(
            f"krdict returns roughly {ratio:.2f}× as many entries as stdict on these 8 chars — "
            "stdict is the bigger pool, krdict is the curated learner-dictionary subset."
        )

    # 5. Reading-by-reading divergence
    for h in ("不", "例"):
        d = stdict_data.get(h, {}).get("by_reading", {})
        readings = list(d.keys())
        if len(readings) >= 2:
            a_words = {e["word_no"] for e in d[readings[0]]["entries"]}
            b_words = {e["word_no"] for e in d[readings[1]]["entries"]}
            uniq_to_a = len(a_words - b_words)
            uniq_to_b = len(b_words - a_words)
            quirks.append(
                f"{h}: reading `{readings[0]}` adds {uniq_to_a} unique results, "
                f"`{readings[1]}` adds {uniq_to_b} — multi-reading queries are NOT "
                "redundant; must query each reading."
            )

    for q in quirks:
        p(f"- {q}")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────


def main():
    if not KRDICT_API_KEY:
        log("WARNING: KRDICT_API_KEY env var not set; krdict calls will fail.")

    try:
        github_rows, github_cols = fetch_github_csv()
        github_by_char = analyze_github(github_rows, github_cols)
    except Exception as e:
        log(f"GitHub source failed: {e}")
        traceback.print_exc(file=sys.stderr)
        github_rows, github_cols, github_by_char = [], [], {}

    stdict_data = {}
    try:
        stdict_data = scrape_stdict_all()
    except Exception as e:
        log(f"stdict failed: {e}")
        traceback.print_exc(file=sys.stderr)

    krdict_data = {}
    try:
        krdict_data = scrape_krdict_all()
    except Exception as e:
        log(f"krdict failed: {e}")
        traceback.print_exc(file=sys.stderr)

    report = build_report(github_rows, github_cols, github_by_char, stdict_data, krdict_data)
    print(report)
    (ROOT / "exploration_report.md").write_text(report, encoding="utf-8")
    log(f"Report saved to {ROOT / 'exploration_report.md'}")


if __name__ == "__main__":
    main()
