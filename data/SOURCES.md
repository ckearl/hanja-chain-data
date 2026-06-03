# Data sources & provenance

## `core_1800.csv` — 한문교육용 기초한자 (MOE Basic Hanja for Korean Education)

- **What**: The Ministry of Education's 中高等學校 漢文敎育用 基礎漢字 — the official "what
  Korean students learn" core. 900 middle-school + 899 high-school characters
  (1,799 total; the canonical "1,800" set, this revision being 1,799 after the
  2000-12-30 / 2007 자형 revision).
- **Source**: Korean Wikipedia, *대한민국 중고등학교 기초한자 목록*, raw wikitext fetched
  via the MediaWiki `action=raw` endpoint. Cached at `raw/sources/wikipedia.wikitext`.
- **Columns**: `hanja` (NFC-normalized), `reading` (representative 음 from the
  source table), `core_level` (`middle` | `high`).
- **Validation**: 1,795 / 1,799 of these chars are present in rycont (after NFC
  normalization) at 한국어문회 grade 8급–3급, confirming this is the high-priority
  core. The grade distribution cuts off cleanly at 3급 (only 4 chars rarer).

## CRITICAL data-quality note: NFC normalization is a hard requirement

rycont's `hanja.csv` stores 9 rows using **CJK Compatibility Ideographs**
(U+F900 block — created for Korean round-trip), e.g. 金 is `U+F90A` not `U+91D1`,
車 is `U+F902`, 不 is `U+F967`. These are visually identical but distinct
codepoints. Every Hanja join key in the pipeline — the core list, rycont, stdict
`hanja_raw`, and krdict `origin` — **must be NFC-normalized** or characters and
compounds will silently fail to bucket. NFC canonically maps the compatibility
ideographs to their unified form.

Four core glyphs are genuine variant pairs (정자 vs 약자) that NFC does *not*
unify because they are distinct unified ideographs:

| core (정자) | rycont (약자) |
|---|---|
| 奬 U+596C | 獎 U+734E |
| 姊 U+59CA | 姉 U+59C9 |
| 產 U+7522 | 産 U+7523 |
| 絕 U+7D55 | 絶 U+7D76 |

These are mapped explicitly in `backfill_chars.json` → `variant_to_rycont` so the
core glyph stays canonical while borrowing rycont's radical/strokes.

## `hanja-grade-dataset/` — rycont 한국어문회 grade dataset

- 5,978 characters with 한국어문회 grade, representative reading, meaning literal,
  radical, strokes, total_strokes.
- Pinned at commit `91a1f49c7f05492f76ce817096b3fb500830f7b9` (2024-06-06).
- `meaning` is a stringified Python literal `[[[meanings],[readings]]]`; multi-
  reading chars carry multiple `[meanings, readings]` pairs.
- Used as: metadata source for core chars (radical/strokes/grade/all readings),
  and the full-scope (5,978) character inventory for the Phase B expansion.
