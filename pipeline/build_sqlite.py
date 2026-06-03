"""Stage 6 — build the SQLite artifact.

    python -m pipeline.build_sqlite --scope core   # -> hanja.sqlite
    python -m pipeline.build_sqlite --scope full   # -> hanja-full.sqlite

Reads staging/{characters,compounds,character_compounds}.jsonl and writes a
flat, indexed SQLite database the app embeds/downloads.
"""

import argparse
import json
import sqlite3

from . import sources as S

SCHEMA = """
PRAGMA journal_mode = OFF;
PRAGMA synchronous = OFF;

CREATE TABLE characters (
  hanja         TEXT PRIMARY KEY,
  primary_sound TEXT,
  level         TEXT,
  is_core       INTEGER NOT NULL DEFAULT 0,
  core_level    TEXT,
  meaning_ko    TEXT,
  meaning_en    TEXT,
  radical       TEXT,
  strokes       INTEGER,
  total_strokes INTEGER,
  source        TEXT NOT NULL
);
CREATE INDEX idx_characters_is_core ON characters(is_core);

CREATE TABLE character_readings (
  hanja      TEXT NOT NULL REFERENCES characters(hanja),
  reading    TEXT NOT NULL,
  meaning_ko TEXT,
  is_primary INTEGER NOT NULL,
  PRIMARY KEY (hanja, reading)
);
CREATE INDEX idx_readings_reading ON character_readings(reading);

CREATE TABLE compounds (
  id                 INTEGER PRIMARY KEY,
  word_ko            TEXT NOT NULL,
  word_ko_raw        TEXT,
  hanja_form         TEXT NOT NULL,
  pos                TEXT,
  definition_ko      TEXT,
  definition_en      TEXT,
  english_gloss      TEXT,
  stdict_word_no     TEXT,
  krdict_target_code TEXT,
  has_english        INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_compounds_word ON compounds(word_ko);
CREATE INDEX idx_compounds_hanja_form ON compounds(hanja_form);
CREATE INDEX idx_compounds_has_english ON compounds(has_english);

CREATE TABLE character_compounds (
  hanja       TEXT NOT NULL REFERENCES characters(hanja),
  compound_id INTEGER NOT NULL REFERENCES compounds(id),
  position    INTEGER NOT NULL,
  PRIMARY KEY (hanja, compound_id, position)
);
CREATE INDEX idx_cc_hanja ON character_compounds(hanja);
CREATE INDEX idx_cc_compound ON character_compounds(compound_id);
"""


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=["core", "full"], default="core")
    args = ap.parse_args()

    db_path = S.ROOT / S.db_filename(args.scope)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)

    chars = load_jsonl(S.STAGING / "characters.jsonl")
    conn.executemany(
        "INSERT INTO characters (hanja, primary_sound, level, is_core, core_level, "
        "meaning_ko, meaning_en, radical, strokes, total_strokes, source) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [(c["hanja"], c["primary_sound"], c["level"], c["is_core"], c["core_level"],
          c["meaning_ko"], c.get("meaning_en"), c["radical"], c["strokes"],
          c["total_strokes"], c["source"])
         for c in chars])
    conn.executemany(
        "INSERT OR IGNORE INTO character_readings (hanja, reading, meaning_ko, is_primary) "
        "VALUES (?,?,?,?)",
        [(c["hanja"], r["reading"], r["meaning_ko"], r["is_primary"])
         for c in chars for r in c["readings"]])

    compounds = load_jsonl(S.STAGING / "compounds.jsonl")
    conn.executemany(
        "INSERT INTO compounds (id, word_ko, word_ko_raw, hanja_form, pos, definition_ko, "
        "definition_en, english_gloss, stdict_word_no, krdict_target_code, has_english) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [(c["id"], c["word_ko"], c["word_ko_raw"], c["hanja_form"], c["pos"],
          c["definition_ko"], c["definition_en"], c["english_gloss"],
          c["stdict_word_no"], c["krdict_target_code"], c["has_english"])
         for c in compounds])

    edges = load_jsonl(S.STAGING / "character_compounds.jsonl")
    conn.executemany(
        "INSERT OR IGNORE INTO character_compounds (hanja, compound_id, position) "
        "VALUES (?,?,?)",
        [(e["hanja"], e["compound_id"], e["position"]) for e in edges])

    conn.commit()
    conn.execute("VACUUM")
    conn.close()

    mb = db_path.stat().st_size / 1e6
    S.log(f"wrote {db_path.name}: {len(chars)} chars, {len(compounds)} compounds, "
          f"{len(edges)} edges ({mb:.1f} MB)")


if __name__ == "__main__":
    main()
