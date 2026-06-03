"""Shared source clients, parsers, paths, and helpers for the build pipeline.

Refactored out of ``explore.py`` so the exploration script and the pipeline
stages share one implementation. The key behavioral differences vs. explore.py:

- No exploration page cap — scrapers paginate to exhaustion (resume-safe via
  cached raw files, so re-runs are cheap).
- ``nfc()`` is applied to every Hanja join key. rycont stores some chars as CJK
  Compatibility Ideographs (U+F900 block) and stdict/krdict may use either form;
  NFC canonicalizes them so characters and compounds bucket correctly. See
  data/SOURCES.md.
"""

import os
import re
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from bs4 import BeautifulSoup, NavigableString

# ── Paths ────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = ROOT / "raw"
STAGING = ROOT / "staging"
RYCONT_CSV = ROOT / "hanja-grade-dataset" / "hanja.csv"

DELAY = 0.5  # polite delay between network requests
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def nfc(s):
    """NFC-normalize. Unifies CJK Compatibility Ideographs with their canonical
    unified form — a hard requirement for every Hanja join key in the pipeline."""
    return unicodedata.normalize("NFC", s) if s else s


# Range of CJK ideographs we treat as "a Hanja character" for chain decomposition.
_HANJA_RE = re.compile(
    r"[㐀-䶿一-鿿豈-﫿\U00020000-\U0002ebef]"
)


def hanja_chars(s):
    """Return the NFC-normalized Hanja characters in a string, in order.

    Used to decompose a compound's ``hanja_raw`` chain into individual chars.
    Non-Hanja (Latin like 'gas化學', digits, punctuation) are dropped.
    """
    return [nfc(c) for c in (s or "") if _HANJA_RE.match(c)]


# ── Source 2: 표준국어대사전 (stdict) scrape ───────────────────────────
STDICT_URL = "https://stdict.korean.go.kr/search/searchResult.do"
STDICT_HEADERS = {
    "User-Agent": UA,
    "Referer": STDICT_URL,
    "Content-Type": "application/x-www-form-urlencoded",
}
# stdict's plain keyword search only returns exact single-word matches; wildcard
# wrapping surfaces every compound containing the syllable.
STDICT_WILDCARD = "*{kw}*"
STDICT_PAGE_SIZE = 50


def stdict_post(keyword, page):
    data = {
        "searchKeyword": keyword,
        "searchKeywordTo": "3",
        "pageSize": str(STDICT_PAGE_SIZE),
        "pageUnit": str(STDICT_PAGE_SIZE),
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
    return int(m.group(1).replace(",", "")) if m else 0


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

        word_raw = a.get_text(strip=False)
        sup = a.find("sup")
        if sup:
            word_raw = word_raw.replace(sup.get_text(), "")
        word = word_raw.strip().lstrip("-").strip()

        href = a.get("href", "")
        m = re.search(r"word_no=(\d+)", href)
        word_no = m.group(1) if m else None

        hanja_span = dt.select_one("span.hanja_font")
        hanja_raw = ""
        if hanja_span:
            hanja_raw = hanja_span.get_text(strip=True).strip("()").strip()

        pos = ""
        if hanja_span:
            nxt = hanja_span.next_sibling
            while nxt is not None and isinstance(nxt, NavigableString) and not nxt.strip():
                nxt = nxt.next_sibling
            if nxt is not None and isinstance(nxt, NavigableString):
                txt = nxt.strip()
                pm = re.search(r"[「\[]([^「」\[\]]+)[」\]]", txt)
                pos = pm.group(1) if pm else txt.strip("「」[]").strip()

        dataline = dt.select_one("font.dataLine")
        definition_ko = dataline.get_text(" ", strip=True) if dataline else ""

        sense_span = dt.select_one("span.t_red1")
        sense = sense_span.get_text(strip=True).strip("「」").strip() if sense_span else ""

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
    nums = [int(p) for p in (s.get_text(strip=True) for s in paging.find_all(["span", "a"]))
            if p.isdigit()]
    return bool(nums) and max(nums) > current_page


# ── Source 3: krdict (한국어기초사전) Open API ─────────────────────────
KRDICT_URL = "https://krdict.korean.go.kr/api/search"
KRDICT_API_KEY = os.environ.get("KRDICT_API_KEY", "")
KRDICT_NUM = 100  # API rejects num<10; effectively caps the result set at 100.


def krdict_call(keyword, start=1, num=KRDICT_NUM, method="exact"):
    params = {
        "key": KRDICT_API_KEY,
        "q": keyword,
        "translated": "y",
        "trans_lang": "1",      # 1 = English
        "method": method,
        "part": "word",
        "num": str(num),
        "start": str(start),
    }
    r = requests.get(KRDICT_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.text


def parse_krdict_xml(xml_text):
    """Return ``(total, entries)``. Each entry carries senses with English
    translations (``trans_lang`` == '영어')."""
    entries = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        log(f"  krdict XML parse error: {e}")
        return 0, entries

    err = root.find("error")
    if err is not None:
        log(f"  krdict API error: {err.findtext('error_code')} {err.findtext('message')}")
        return 0, entries

    total_el = root.find("total")
    total = int(total_el.text) if total_el is not None and total_el.text else 0

    for item in root.findall("item"):
        senses = []
        for sense in item.findall("sense"):
            translations = [{
                "trans_lang": (tr.findtext("trans_lang") or "").strip(),
                "trans_word": (tr.findtext("trans_word") or "").strip(),
                "trans_dfn": (tr.findtext("trans_dfn") or "").strip(),
            } for tr in sense.findall("translation")]
            senses.append({
                "sense_no": (sense.findtext("sense_no") or "").strip(),
                "definition": (sense.findtext("definition") or "").strip(),
                "translations": translations,
            })
        entries.append({
            "target_code": (item.findtext("target_code") or "").strip(),
            "word": (item.findtext("word") or "").strip(),
            "origin": (item.findtext("origin") or "").strip(),  # Hanja notation
            "pos": (item.findtext("pos") or "").strip(),
            "senses": senses,
        })
    return total, entries


# ── 두음법칙 (initial-sound rule) syllable expansion ───────────────────
# rycont stores Sino-Korean readings in dictionary form with 두음법칙 NOT
# applied (例→례, 女→녀, 不→불). But word-initially those surface as 예/여/부,
# so compounds are filed under both syllables in stdict. For scrape COVERAGE we
# query both the dictionary reading and its word-initial variant. (This is not a
# claim about the character's readings — it's which syllable buckets to sweep.)
_HANGUL_BASE = 0xAC00
_Y_I_NUCLEI = {2, 3, 6, 7, 12, 17, 20}  # ㅑㅒㅕㅖㅛㅠㅣ — y-glide / i vowels


def initial_law_variants(syllable):
    """Return {syllable} plus any 두음법칙 word-initial variant(s).

    ㄹ-onset: → ㅇ before a y/i vowel (례→예, 료→요, 리→이), else → ㄴ (로→노, 락→낙).
    ㄴ-onset: → ㅇ before a y/i vowel (녀→여, 니→이). Other onsets are unchanged.
    """
    out = {syllable}
    if len(syllable) != 1:
        return out
    code = ord(syllable) - _HANGUL_BASE
    if not (0 <= code < 11172):
        return out
    onset = code // 588
    rest = code % 588
    nucleus = rest // 28
    coda = rest % 28
    new_onset = None
    if onset == 5:  # ㄹ
        new_onset = 11 if nucleus in _Y_I_NUCLEI else 2  # ㅇ or ㄴ
    elif onset == 2 and nucleus in _Y_I_NUCLEI:  # ㄴ before y/i
        new_onset = 11  # ㅇ
    if new_onset is not None and new_onset != onset:
        out.add(chr(_HANGUL_BASE + (new_onset * 21 + nucleus) * 28 + coda))
    return out


# ── Shared normalization for cross-source word matching ───────────────
def norm_word(w):
    """Normalize a Korean headword for cross-source matching: strip the stdict
    phrase marker '^' and bound-morpheme marker '-'."""
    return (w or "").replace("^", "").replace("-", "").strip()


# ── Scope helpers ─────────────────────────────────────────────────────
def db_filename(scope):
    return "hanja.sqlite" if scope == "core" else "hanja-full.sqlite"


def ensure_dirs():
    for d in (DATA, RAW, STAGING, RAW / "stdict", RAW / "krdict", RAW / "sources"):
        d.mkdir(parents=True, exist_ok=True)
