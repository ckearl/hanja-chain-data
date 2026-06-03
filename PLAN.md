# Plan: comprehensive Hanja dictionary build pipeline

## Context

We've finished the exploration phase (`/Users/toph/projects/hanja-app/exploration_report.md`) and confirmed:

- **rycont's 5,978-char CSV** is solid as a master list (100% field population), with one known gap: 不 and a few other basic chars aren't graded by 한국어문회 so they're missing.
- **stdict** (표준국어대사전) holds compound-word coverage but requires `*reading*` wildcards, paginates in 가나다 order, and `hanja_raw` is populated 100% on compounds (the critical answer that makes character-chain building possible).
- **krdict** (한국어기초사전 API) gives 100% English translations on its entries but is **effectively capped at 100 results per call** — `total=418` but `start=101` returns zero items.
- Multi-reading characters need separate per-reading queries (e.g. 不 needs both 불 and 부); their result sets barely overlap.

User scope decisions:
- Inventory: **한문교육용 기초한자 1,800 (core) FIRST**, then layer rycont's 5,978 on top as supplementary. Build & ship the 1,800 first; the rycont expansion is a follow-on phase that runs the same pipeline against the larger character list.
- Depth: **char metadata + compound words + English where available**
- English strategy: **krdict only, no LLM fallback** — words not in krdict stay Korean-only
- Output: **single SQLite file** the app embeds/downloads

Intended outcome: one shipped `hanja.sqlite` (core build) covering the 1,800 한문교육용 기초한자, with all their readings, every compound word found via per-syllable stdict scraping, and English definitions merged from krdict where present. A subsequent `hanja-full.sqlite` adds rycont's remaining ~4,200 characters.

---

## Architectural insight: scrape by syllable, bucket by character

Instead of scraping stdict per-character (1,800 chars × ~2 readings = redundant overlapping scrapes), scrape per **unique Sino-Korean syllable**. The 1,800 core covers ~300 distinct syllables; the rycont 5,978 covers ~400. One `*학*` scrape captures every compound containing 學, 鶴, 瘧, 虐, etc. simultaneously — then filter by Hanja character into per-char buckets.

**Key efficiency**: when we later expand from 1,800 → rycont 5,978, most of the ~400 syllables are already scraped. The expansion only needs to scrape the ~100 syllables introduced by the new characters, plus re-bucket the existing scraped data against the expanded character list. The core scrape is the long pole.

Rough volume budget at 0.5s/request:
- **Core (1,800) stdict scrape**: ~300 syllables × ~80 pages avg × 0.5s ≈ **3–4 hours** (one-time)
- **Core krdict**: ~300 syllables × 1 call × 0.5s ≈ **3 minutes**
- **Rycont expansion**: ~100 additional syllables × ~80 pages × 0.5s ≈ **1–1.5 hours** extra
- Disk: raw HTML/XML ~1–2 GB for core, ~2–4 GB after expansion; final SQLite likely <500 MB

---

## Pipeline stages

### Stage 1 — Build the master character list (`build_char_list.py`)

Run in two modes, controlled by `--scope core|full`:

**Core mode (default, 1,800 chars):**
- Load `data/core_1800.csv` — the 한문교육용 기초한자 (Ministry of Education Basic Hanja for Korean Language Education). Source candidates: published MOE list (PDF, needs OCR), or a maintained GitHub mirror (e.g. `koreanstudies/hanmun-1800` or similar — pick one and pin the commit). The list itself is ~900 middle-school + ~900 high-school characters.
- This list typically carries only Hanja + reading + meaning gloss. We use it for the character inventory; for radical/strokes data we fall back to rycont where the character is present, and Unihan otherwise.

**Full mode (rycont expansion, 5,978 chars):**
- Start from core mode output, then union with `hanja-grade-dataset/hanja.csv`. Keep `source` field distinguishing rows that came from core, rycont, or backfill.

**For both modes:**
- Parse the `meaning` column from rycont (stringified Python literal `[[[meanings], [readings]]]`) via `ast.literal_eval`. Multi-reading chars carry multiple `[meanings, readings]` pairs.
- Extract all readings per character (not just primary) into a normalized table.
- Apply a hand-maintained backfill list (`data/backfill_chars.json`) for any chars referenced by stdict compounds but missing from both the core list and rycont (start with 不 if it's not in the core 1800; grow during stage 5).
- Emit the de-duplicated list of unique syllables → drives stage 3.

### Stage 2 — Enrich character metadata from Unihan (optional, `enrich_unihan.py`)

- The Unicode Unihan database has `kKorean`, `kDefinition`, `kRSUnicode` (radical + residual strokes), `kFrequency`. Cached locally as `Unihan_Readings.txt` etc.
- Use it to: cross-check radicals/strokes, fill missing English short-glosses for the per-character entry (separate from word-level translations — this is just "what does this character mean").
- Optional but cheap; can defer.

### Stage 3 — Scrape stdict by syllable (`scrape_stdict.py`)

- Iterate the unique syllable list from stage 1 (core mode → ~300 syllables; full mode → ~400, but ~300 already cached from core run).
- For each syllable, POST `*{syllable}*` and paginate **all pages** (no exploration cap), 0.5s delay.
- Save raw HTML to `raw/stdict/{syllable}_p{N}.html` (resume-safe: skip pages that already exist — this is what makes the rycont expansion cheap).
- Parse each entry with the existing parser from `explore.py` (`parse_stdict_html`).
- Reuse existing `STDICT_HEADERS` and the form-body shape from `explore.py:STDICT_URL`.
- Write parsed entries to `staging/stdict_entries.jsonl` (append, one entry per line).

### Stage 4 — Fetch krdict by syllable (`scrape_krdict.py`)

- Iterate the same syllable list.
- For each syllable, single GET call: `q={syllable}&num=100&start=1&method=exact&translated=y&trans_lang=1`.
- Save raw XML to `raw/krdict/{syllable}.xml`.
- Reuse `parse_krdict_xml` from `explore.py`.
- Write parsed entries to `staging/krdict_entries.jsonl`.
- Acknowledge the cap: we get the first 100 only. That's an accepted limit given user's "krdict only, partial English" choice.

### Stage 5 — Bucket compounds per character + merge sources (`bucket_and_merge.py`)

For each entry from stdict_entries.jsonl:
- Look at `hanja_raw` (which is the actual Hanja chain like 加工冶金學).
- For each Hanja character in `hanja_raw` that is in our master list, record this entry as a compound containing that character.

For each entry from krdict_entries.jsonl:
- Use the `origin` field similarly.

Merge keys: normalize Korean word by stripping `^` (phrase marker) and `-` (bound morpheme marker). When stdict and krdict both have a normalized-equal word with the same Hanja form, merge into one compound record (stdict Korean def + krdict English def).

Output: `staging/compounds.jsonl` (one row per unique compound) and `staging/character_compounds.jsonl` (many-to-many edges char↔compound).

### Stage 6 — Build SQLite (`build_sqlite.py`)

Schema (kept flat and indexed):

```sql
CREATE TABLE characters (
  hanja        TEXT PRIMARY KEY,
  primary_sound TEXT NOT NULL,
  level        TEXT,        -- rycont 한국어문회 grade ('8급', '특급Ⅱ', NULL if not in rycont)
  is_core      INTEGER NOT NULL DEFAULT 0,  -- 1 if in 한문교육용 기초한자 1800
  core_level   TEXT,        -- 'middle' | 'high' | NULL — which half of the 1800
  meaning_ko   TEXT,        -- primary meaning, e.g. '배울'
  radical      TEXT,
  strokes      INTEGER,
  total_strokes INTEGER,
  source       TEXT NOT NULL  -- 'core' | 'rycont' | 'backfill' | 'unihan'
);
CREATE INDEX idx_characters_is_core ON characters(is_core);

CREATE TABLE character_readings (
  hanja   TEXT NOT NULL REFERENCES characters(hanja),
  reading TEXT NOT NULL,
  meaning_ko TEXT,                  -- per-reading meaning
  is_primary INTEGER NOT NULL,      -- 1 if this matches characters.primary_sound
  PRIMARY KEY (hanja, reading)
);
CREATE INDEX idx_readings_reading ON character_readings(reading);

CREATE TABLE compounds (
  id            INTEGER PRIMARY KEY,
  word_ko       TEXT NOT NULL,       -- normalized: no ^ or -
  word_ko_raw   TEXT,                -- original stdict form (e.g. 가공^야금학) for display
  hanja_form    TEXT NOT NULL,       -- e.g. 加工冶金學
  pos           TEXT,                -- '명사' etc., NULL if unknown
  definition_ko TEXT,                -- from stdict (or krdict if stdict missing)
  definition_en TEXT,                -- from krdict if available, else NULL
  stdict_word_no TEXT,
  krdict_target_code TEXT,
  has_english   INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_compounds_word ON compounds(word_ko);
CREATE INDEX idx_compounds_hanja_form ON compounds(hanja_form);

CREATE TABLE character_compounds (
  hanja       TEXT NOT NULL REFERENCES characters(hanja),
  compound_id INTEGER NOT NULL REFERENCES compounds(id),
  position    INTEGER NOT NULL,      -- 0-based index of this hanja in hanja_form
  PRIMARY KEY (hanja, compound_id, position)
);
CREATE INDEX idx_cc_hanja ON character_compounds(hanja);
CREATE INDEX idx_cc_compound ON character_compounds(compound_id);
```

Notes:
- `pos` is left NULL when stdict didn't tag it (the noun-phrase entries with `^`). The app can render those as "phrase" or omit POS.
- `has_english` denormalized for fast filtering ("show me only translated compounds").
- `position` enables app features like "click each character to see its other compounds at this position."

### Stage 7 — Validate & export (`validate.py`)

Sanity checks:
- Every Hanja in `characters` has at least one row in `character_readings`.
- Every `compound.hanja_form` decomposes into characters all present in `characters` (flag and add to backfill list if not).
- `definition_ko` is non-null for >99% of compounds.
- Spot-check: 학교 lands under 學, 校; both have many compounds; multi-reading chars (不, 例) have entries from both readings.
- Print per-syllable coverage table.

Emit `hanja.sqlite` at project root.

---

## Files to create

```
/Users/toph/projects/hanja-app/
├── pipeline/
│   ├── __init__.py
│   ├── sources.py              # extracted from explore.py: STDICT/krdict clients + parsers
│   ├── build_char_list.py      # supports --scope core|full
│   ├── enrich_unihan.py        # optional
│   ├── scrape_stdict.py        # syllable iterator; resume-safe
│   ├── scrape_krdict.py
│   ├── bucket_and_merge.py
│   ├── build_sqlite.py         # supports --scope core|full → hanja.sqlite | hanja-full.sqlite
│   └── validate.py
├── data/
│   ├── core_1800.csv           # 한문교육용 기초한자 (sourced from MOE/GitHub mirror, pinned)
│   ├── backfill_chars.json     # hand-maintained
│   └── (existing hanja-grade-dataset/)
├── raw/                        # large; gitignored
│   ├── stdict/                 # shared across scopes (resume-safe)
│   └── krdict/
├── staging/                    # large; gitignored
│   ├── stdict_entries.jsonl
│   ├── krdict_entries.jsonl
│   ├── compounds.jsonl
│   └── character_compounds.jsonl
├── hanja.sqlite                # core 1,800 artifact
├── hanja-full.sqlite           # full rycont expansion artifact (built later)
└── PLAN.md                     # this plan, mirrored from ~/.claude/plans/
```

**Reused from existing `explore.py`:**
- `STDICT_URL`, `STDICT_HEADERS`, form-body shape
- `parse_stdict_html`, `parse_total`, `has_more_pages`
- `parse_krdict_xml`
- 0.5s delay convention

I'd refactor those into `pipeline/sources.py` so both `explore.py` and the pipeline scripts share them rather than duplicate.

---

## Verification

**Phase A — Core 1,800 build:**

1. `python -m pipeline.build_char_list --scope core` → confirm `staging/characters.jsonl` has ~1,800 rows; unique-syllables file has ~300 entries.
2. `python -m pipeline.scrape_stdict --scope core --syllable 학` (single-syllable smoke test before full run) → confirm pagination completes, 학교 appears, raw files saved.
3. `python -m pipeline.scrape_stdict --scope core` (full run; resume-safe; expect 3–4 hrs).
4. `python -m pipeline.scrape_krdict --scope core` (~3 min).
5. `python -m pipeline.bucket_and_merge --scope core` → confirm `staging/compounds.jsonl` non-empty, normalized words look right (no `^` or `-`), merged records carry both `definition_ko` and `definition_en` where applicable.
6. `python -m pipeline.build_sqlite --scope core` → confirm `hanja.sqlite` exists.
7. `python -m pipeline.validate --scope core` → all sanity checks pass; spot-check via sqlite3 shell:
   ```
   sqlite3 hanja.sqlite \
     "SELECT c.word_ko, c.definition_en FROM compounds c
        JOIN character_compounds cc ON cc.compound_id=c.id
       WHERE cc.hanja='學' AND c.has_english=1 LIMIT 10;"
   ```
   Expect 학교, 학생, 대학, etc. with English translations.

**Phase B — Rycont expansion (run after Phase A ships):**

8. `python -m pipeline.build_char_list --scope full` → ~5,978 rows including all of Phase A.
9. `python -m pipeline.scrape_stdict --scope full` → resume-safe; only fetches new syllables (~100 new × 80 pages × 0.5s ≈ 1–1.5 hrs).
10. `python -m pipeline.scrape_krdict --scope full` → ~7 min total (re-fetches new syllables).
11. `python -m pipeline.bucket_and_merge --scope full` → reprocesses all staged entries against the expanded character set, so previously-orphaned compound characters get connected.
12. `python -m pipeline.build_sqlite --scope full` → emits `hanja-full.sqlite`.
13. `python -m pipeline.validate --scope full`.

---

## Open decisions deferred to implementation time

- **Source for the 1,800 core list.** Stage 1 needs `data/core_1800.csv`. Options:
  - Manually transcribe from MOE's 한문교육용 기초한자 reference PDF (slow, authoritative).
  - Use a public GitHub mirror (faster but requires picking a maintained one and pinning the commit).
  - Cross-check: every 한문교육용 char also has a rycont row at 한국어문회 grade 4급 or higher. We can validate the sourced list against rycont as a sanity check.
- Exact backfill list — grow during stage 5 when un-mapped Hanja appear in `hanja_form` values.
- Whether to include stdict entries with `pos='어미'` (verb endings like ㄹ사) — propose: filter out entries where `pos` ∈ {어미, 조사} since they don't aid Hanja study.
- Compound ranking/sorting for display (frequency? has_english first?) — punt to a `display_order` column we can backfill later from frequency data.
