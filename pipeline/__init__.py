"""Hanja dictionary build pipeline.

Stages (run as ``python -m pipeline.<stage> --scope core|full``):

1. build_char_list  -> staging/characters.jsonl, staging/syllables.txt
2. enrich_unihan    -> (optional) backfills radical/strokes/gloss
3. scrape_stdict    -> raw/stdict/, staging/stdict_entries.jsonl
4. scrape_krdict    -> raw/krdict/, staging/krdict_entries.jsonl
5. bucket_and_merge -> staging/compounds.jsonl, staging/character_compounds.jsonl
6. build_sqlite     -> hanja.sqlite | hanja-full.sqlite
7. validate         -> sanity checks + coverage report
"""
