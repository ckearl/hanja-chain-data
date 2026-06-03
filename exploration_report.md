# Hanja dictionary data exploration report

_8 test characters; generated 2026-05-31 20:42_

> **Note on stdict search**: plain `q=학` returns only the 6 single-syllable entries. To surface compound words containing the syllable (essential for the hanja-chain analysis), we search with `*학*` wildcards. Pages capped at 4 per (char, reading) — sample size, not exhaustive collection.

## Source 1 — rycont/hanja-grade-dataset (GitHub CSV)

- Rows: **5978**
- Columns: `['main_sound', 'level', 'hanja', 'meaning', 'radical', 'strokes', 'total_strokes']`

### Field population
- `main_sound`: 5978/5978 (100%)
- `level`: 5978/5978 (100%)
- `hanja`: 5978/5978 (100%)
- `meaning`: 5978/5978 (100%)
- `radical`: 5978/5978 (100%)
- `strokes`: 5978/5978 (100%)
- `total_strokes`: 5978/5978 (100%)

### Sample record (學)
```json
{
  "main_sound": "학",
  "level": "8급",
  "hanja": "學",
  "meaning": "[[['배울'], ['학']]]",
  "radical": "子",
  "strokes": "13",
  "total_strokes": "16"
}
```

### Coverage on our 8 test chars
| Hanja | match count | level | meaning | radical | strokes |
|---|---:|---|---|---|---:|
| 學 | ✓ 1 | 8급 | [[['배울'], ['학']]] | 子 | 16 |
| 不 | ✗ 0 | — | — | — | — |
| 藝 | ✓ 1 | 4급Ⅱ | [[['재주'], ['예']]] | 艸 | 19 |
| 例 | ✓ 1 | 6급 | [[['법식'], ['례']]] | 人 | 8 |
| 四 | ✓ 1 | 8급 | [[['넉'], ['사']]] | 囗 | 5 |
| 死 | ✓ 1 | 6급 | [[['죽을'], ['사']]] | 歹 | 6 |
| 愛 | ✓ 1 | 6급 | [[['사랑'], ['애']]] | 心 | 13 |
| 龍 | ✓ 1 | 4급 | [[['용'], ['룡']]] | 龍 | 16 |

## Source 2 — 표준국어대사전 (stdict scrape)

### Per-character coverage (total returned vs. Hanja-matched)

| Hanja | Readings | Total unique returned | Matched | Noise % |
|---|---|---:|---:|---:|
| 學 | 학 | 200 | 179 | 10% |
| 不 | 불/부 | 399 | 82 | 79% |
| 藝 | 예 | 200 | 59 | 70% |
| 例 | 례/예 | 400 | 65 | 83% |
| 四 | 사 | 200 | 0 | 100% |
| 死 | 사 | 200 | 8 | 96% |
| 愛 | 애 | 200 | 56 | 72% |
| 龍 | 용 | 200 | 3 | 98% |

### Field population across all matched entries
- `word`: 452/452 (100%)
- `word_no`: 452/452 (100%)
- `hanja_raw`: 452/452 (100%)
- `pos`: 245/452 (54%)
- `sense`: 20/452 (4%)
- `definition_ko`: 452/452 (100%)

### Sample stdict entry (學)
```json
{
  "word": "가공^야금학",
  "word_no": "311",
  "hanja_raw": "加工冶金學",
  "pos": "",
  "sense": "",
  "definition_ko": "『공업』 금속에 기계적 힘이 가해졌을 경우에 나타나는 일련의 현상을 연구하는 학문."
}
```

### POS distribution (matched entries, all chars)
- `(none)`: 207
- `명사`: 205
- `동사`: 32
- `형용사`: 7
- `Ⅰ`: 1

Noun/verb share: **237/452 = 52%**
Non-N/V (filter candidates): **48%**

### Hanja notation on compound words (CRITICAL)
- Compound (len > 1) matched entries: **451**
- With non-empty `hanja_raw`: **451 (100%)**
- `hanja_raw` length ≥ word length: **90/451**

Sample compound-word entries:
  - 가공^야금학 (加工冶金學)  pos=—
  - 가금-학 (家禽學)  pos=명사
  - 가두^문학 (街頭文學)  pos=—
  - 가스^화학^공업 (gas化學工業)  pos=—
  - 가전-학 (家傳學)  pos=명사
  - 가정지학 (家庭之學)  pos=명사
  - 가정-학 (家政學)  pos=명사
  - 가정-학 (家庭學)  pos=명사

### 四 vs 死 collision check
- 四 matched entries: 0
- 死 matched entries: 8
- Overlap (same word_no in both filtered sets): **0**
- Total unique results for 사-search (from 四 collection): 200

### Multi-reading handling (不, 例)

**不**
  - reading `불`: 200 entries returned, 70 match 不
  - reading `부`: 200 entries returned, 12 match 不

**例**
  - reading `례`: 200 entries returned, 65 match 例
  - reading `예`: 200 entries returned, 0 match 例

## Source 3 — krdict (한국어기초사전 Open API)

### Per-character coverage (exact vs. include)

| Hanja | exact total | exact matched | include total | include matched |
|---|---:|---:|---:|---:|
| 學 | 100 | 89 | 100 | 89 |
| 不 | 200 | 86 | 200 | 86 |
| 藝 | 100 | 9 | 100 | 9 |
| 例 | 198 | 48 | 198 | 48 |
| 四 | 100 | 8 | 100 | 8 |
| 死 | 100 | 5 | 100 | 5 |
| 愛 | 100 | 45 | 100 | 45 |
| 龍 | 100 | 8 | 100 | 8 |

### Field population — exact-matched entries
- `target_code`: 298/298 (100%)
- `word`: 298/298 (100%)
- `origin`: 298/298 (100%)
- `pos`: 289/298 (96%)
- Senses w/ Korean def: 351/351
- Senses w/ English translation: 351/351 (100%)

### Sample krdict entry (學)
```json
{
  "target_code": "88476",
  "word": "-학",
  "origin": "學",
  "pos": "접사",
  "senses": [
    {
      "sense_no": "",
      "definition": "‘학문’의 뜻을 더하는 접미사.",
      "translations": [
        {
          "trans_lang": "영어",
          "trans_word": "-hak",
          "trans_dfn": "A suffix used to mean \"a branch of study.\""
        }
      ]
    }
  ]
}
```

### krdict POS distribution (matched, exact)
- `명사`: 209
- `형용사`: 35
- `동사`: 21
- `관형사`: 11
- `(none)`: 9
- `부사`: 7
- `접사`: 4
- `수사`: 2

## Cross-source overlap (stdict ∩ krdict, by Korean word)

> **Sampling caveat** — this comparison is dominated by an ordering artifact, not a real coverage gap:
>
> - stdict returns results in dictionary (가나다) order. With our 4-page cap (200 entries), the stdict sample for 學 is entirely 가-prefix words like 가공^야금학, 가금-학, 가전-학… Common words (학교, 학생, 대학) sort later and are not in the sample.
> - krdict, by contrast, is a curated 5k-word learner dictionary; its result set IS the common-word universe (학교, 학생, 대학, 학과…).
>
> So the two sets barely overlap *in this sample*. The schema-design takeaway is: krdict gives the basic-vocabulary core; stdict gives the long tail of specialized/technical/dated words. To measure real overlap we'd need exhaustive stdict scraping, not the first 200 alphabetical entries.
>
> Also: stdict words include phrase markers `^` (space) and hyphenation `-`. We normalize both sides before comparison.

| Hanja | stdict matched | krdict matched (exact) | overlap (normalized) | krdict English % |
|---|---:|---:|---:|---:|
| 學 | 177 | 84 | 0 | 100% |
| 不 | 82 | 82 | 0 | 100% |
| 藝 | 58 | 8 | 0 | 100% |
| 例 | 65 | 46 | 1 | 100% |
| 四 | 0 | 6 | 0 | 100% |
| 死 | 8 | 5 | 0 | 100% |
| 愛 | 52 | 44 | 0 | 100% |
| 龍 | 3 | 8 | 0 | 100% |

**Average English-translation rate among krdict matches: ~100%**

Key insight: krdict's curated subset is fully translated, but it is small (~50 common words per character). For full Hanja-app coverage we'd use **krdict for the common-word core** (English translations free) and **stdict for the long tail** (Korean definition only — would need LLM translation fallback for English).

_(Raw counts: 1 normalized overlap out of 445 stdict / 283 krdict — see sampling caveat above.)_

## Per-source gotchas

### rycont GitHub CSV
- ⚠️  Characters MISSING from the dataset: ['不']
  (The set covers 8급–특급Ⅱ from 한국어문회. Some basic chars like 不 are not listed by 한국어문회.)
- `meaning` is a stringified Python literal: `[[[korean_meaning(s)], [korean_reading(s)]]]`. Multi-reading characters carry multiple `[[meanings], [readings]]` pairs in this list.
- One row per Hanja — no duplication by reading. main_sound carries the primary reading only.

### stdict scrape
- Wildcard `*{kw}*` is required to surface compound words. Plain keyword search returns only exact single-syllable matches.
- `pos` is empty for noun-phrase entries (those containing `^`), since stdict does not tag phrases — this explains the ~54% pos population.
- `word` strings carry phrase/morpheme markers: `^` separates phrase parts (가공^야금학), `-` separates a bound morpheme (가금-학). Normalize before any cross-source match.
- ⚠️  四 returned 0 matched entries in the first 200 사-results (out of 19,326 total). stdict result ordering surfaces other 사-Hanja (死, 私, 史, 思, 寺, 司, 砂…) before 四. Deeper pagination or a more selective search is needed to find 四 compounds.

### krdict API
- ⚠️  **Pagination is broken or capped**: the API reports e.g. `total=418` for `q=학&num=100`, but `start=101` returns ZERO `<item>` elements. Each call effectively caps at 100 results. The `total` field is a count of matches that exist but cannot all be fetched by paginating with `start`.
- `exact` and `include` methods returned identical totals on every test character — the `method` parameter appears not to differentiate for syllable queries.
- `origin` field carries the Hanja. It is populated 100% on matched entries. May contain non-Hanja characters (e.g. `gas化學工業` in the 學 sample).
- Every matched entry had at least one English translation (100%) — krdict's curated 5k-word subset is fully translated.

## Surprises & schema-design flags

- ✓ stdict compound words populate hanja_raw 100% of the time — character-chain build is feasible from this source.
- ✓ 四 / 死 separate cleanly via hanja_raw filter (no word_no overlap).
- POS filter: 47% of stdict entries are non-noun/verb. If we want only N/V we should filter early.
- krdict returns roughly 0.64× as many entries as stdict on these 8 chars — stdict is the bigger pool, krdict is the curated learner-dictionary subset.
- 不: reading `불` adds 199 unique results, `부` adds 199 — multi-reading queries are NOT redundant; must query each reading.
- 例: reading `례` adds 200 unique results, `예` adds 200 — multi-reading queries are NOT redundant; must query each reading.