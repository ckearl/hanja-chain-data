# Hanja Chain — data pipeline

Builds `hanja.sqlite` — a library of Hanja character metadata + compound words
with Korean definitions and (where krdict has them) English translations.

This is the data side of **[Hanja Chain](https://github.com/ckearl/hanja-chain-app)**, a
mobile app for learning Hanja through the Korean words that use them. The app ships a
trimmed copy of this database. The current core build covers 1,799 characters and
312k compound words, scraped from 표준국어대사전 and merged with 한국어기초사전, the
한국어문회 grade lists and Unicode Unihan.

The built database and the multi-GB scrape caches aren't committed. Run the pipeline
to regenerate them. `exploration_report.md` and `explore.py` are the initial survey of
the sources that shaped `PLAN.md`.

- **Core scope** (`--scope core`): the 한문교육용 기초한자 (~1,799 chars; what Korean
  students learn). Ships first.
- **Full scope** (`--scope full`): adds rycont's full 5,978 characters, reusing
  the core scrape. Run after core ships.

See `PLAN.md` for design and `data/SOURCES.md` for provenance + the NFC /
variant-glyph data-quality notes.

## Prereqs

```bash
git submodule update --init      # hanja-grade-dataset (rycont, pinned)
export KRDICT_API_KEY=...        # required for stage 4 (English translations); free key from krdict.korean.go.kr/openApi
pip install requests beautifulsoup4
```

## Run order (core)

```bash
python -m pipeline.build_char_list --scope core   # -> staging/characters.jsonl, syllables.txt
python -m pipeline.enrich_unihan   --scope core   # optional: + English char glosses
python -m pipeline.scrape_stdict   --scope core   # ~a day; resume-safe (see below)
python -m pipeline.scrape_krdict   --scope core   # ~25 min (100-cap per syllable)
python -m pipeline.bucket_and_merge --scope core  # -> compounds + edges
python -m pipeline.build_sqlite    --scope core   # -> hanja.sqlite
python -m pipeline.validate        --scope core
```

Swap `core` → `full` for the expansion phase (the stdict scrape reuses every
syllable already cached, so it only fetches the new ones).

## How long the stdict scrape takes

This is the long pole — **budget roughly a full day (~20–30 h)** for the 415
core syllables, and **~2–3 GB** of cached HTML. The bottleneck is stdict's own
response latency: measured at **~3.5–4 s per page** (50 entries/page), so our
0.5 s politeness delay is minor next to it. Syllables vary widely — 갑 is 13
pages, 가 is 218, 사 ~387 — and the first 11 (ㄱ) average ~74 pages each.

Progress is logged per syllable plus a heartbeat every 25 pages, so you can see
it working:

```
stdict scrape: 415 syllable(s), scope=core (1 already done, 414 to go)
  [1/415] 가: total 10855 -> ~218 pages
  [1/415] 가: page 25/218 (1250 entries, 0s)      # cached pages fly by
  [1/415] 가: page 150/218 (7500 entries, 61s)
  [1/415] 가: DONE 10855 entries (reported total 10855)
  [2/415] 각: total 3444 -> ~69 pages
  ...
```

## Resume safety (important)

It is resume-safe at two levels:

- `raw/stdict/{syllable}_p{N}.html` — a cached page is read, never re-fetched.
- `staging/stdict/{syllable}.jsonl` — a syllable with this file is skipped
  entirely unless `--force`. Only written once a syllable fully completes, so an
  interrupted syllable safely re-runs (reusing its cached pages).

So you can kill and restart `scrape_stdict` freely. Given the ~day-long runtime,
run it under `tmux`/`screen` (survives a dropped SSH session or closed terminal;
`nohup … &` does not survive sleep/reboot):

```bash
tmux new -s scrape
python -m pipeline.scrape_stdict --scope core 2>&1 | tee scrape.log
# detach: Ctrl-b then d   |   reattach: tmux attach -t scrape
```

If it is interrupted, just rerun the same command — it picks up where it left off.

To shave a few hours you can lower `DELAY` in `pipeline/sources.py` (stdict's own
latency already paces requests), but the default 0.5 s is the polite choice.

⚠️ Do **not** use `--max-pages` for a real run — it caps pages per syllable
(smoke-test only) and the resulting partial cache would then be skipped on later
full runs. To re-scrape a syllable that was capped, delete its
`raw/stdict/{syl}_p*.html` and `staging/stdict/{syl}.jsonl` first.

## Smoke test (single syllable, seconds)

```bash
python -m pipeline.build_char_list  --scope core
python -m pipeline.scrape_stdict     --syllable 학          # full, unbounded
python -m pipeline.scrape_krdict     --syllable 학
python -m pipeline.bucket_and_merge  --scope core
python -m pipeline.build_sqlite      --scope core
python -m pipeline.validate          --scope core
```

## Output schema

`characters`, `character_readings`, `compounds`, `character_compounds` — flat and
indexed. `compounds.english_gloss` is the concise translation (e.g. "university"),
`compounds.definition_en` the full English definition; `has_english` flags rows
that have either. `character_compounds.position` is the 0-based index of the
character within the compound's Hanja chain. See `pipeline/build_sqlite.py` for
the exact DDL.

## Credits & licenses

Pipeline code: [MIT](LICENSE). The data it collects belongs to its sources:

| Source | Used for | Terms |
|---|---|---|
| 국립국어원 [표준국어대사전](https://stdict.korean.go.kr/) | compound words, Hanja forms, Korean definitions | CC BY-SA 2.0 KR |
| 국립국어원 [한국어기초사전](https://krdict.korean.go.kr/) (Open API) | learner vocabulary, English translations | CC BY-SA 2.0 KR |
| [Korean Wikipedia](https://ko.wikipedia.org/wiki/대한민국_중고등학교_기초한자_목록) | 1,800 basic-education Hanja list (`data/core_1800.csv`) | CC BY-SA 4.0 |
| 한국어문회, via [rycont/hanja-grade-dataset](https://github.com/rycont/hanja-grade-dataset) (submodule) | grades, readings, radicals, strokes | © 한국어문회 |
| [Unicode Unihan](https://www.unicode.org/charts/unihan.html) | English character glosses | Unicode License v3 |

The sample files in `parsed/` and anything you build with this pipeline inherit those
terms. Databases built from it are CC BY-SA. Scraping is rate-limited (`DELAY` in
`pipeline/sources.py`); please keep it polite.
