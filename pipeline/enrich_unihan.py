"""Stage 2 (optional) — enrich character metadata from the Unicode Unihan DB.

    python -m pipeline.enrich_unihan --scope core

rycont already supplies radical/strokes/Korean meaning for ~100% of core chars,
so this stage is optional. Its value is a per-character ENGLISH gloss
(Unihan ``kDefinition``), plus a cross-check / backfill for radical
(``kRSUnicode``) and total strokes (``kTotalStrokes``) on any char rycont lacks.

It edits staging/characters.jsonl in place (adds ``meaning_en`` and fills any
null radical/strokes), so run it AFTER build_char_list and BEFORE build_sqlite.
Idempotent. Downloads + caches Unihan.zip under data/unihan/ on first run.
"""

import argparse
import io
import json
import urllib.request
import zipfile

from . import sources as S

UNIHAN_URL = "https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip"
UNIHAN_DIR = S.DATA / "unihan"
NEEDED = ("Unihan_Readings.txt", "Unihan_IRGSources.txt", "Unihan_DictionaryLikeData.txt")

# Kangxi radical number -> radical character, for kRSUnicode backfill.
_KANGXI_BASE = 0x2F00  # ⼀ is radical 1 at U+2F00


def ensure_unihan():
    UNIHAN_DIR.mkdir(parents=True, exist_ok=True)
    if all((UNIHAN_DIR / n).exists() for n in NEEDED):
        return
    S.log(f"downloading Unihan.zip from {UNIHAN_URL} ...")
    with urllib.request.urlopen(UNIHAN_URL, timeout=120) as r:
        blob = r.read()
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for n in NEEDED:
            if n in z.namelist():
                (UNIHAN_DIR / n).write_bytes(z.read(n))
    S.log("Unihan files cached under data/unihan/")


def load_fields(wanted):
    """Parse the cached Unihan .txt files into {char: {field: value}} for the
    requested field names."""
    out = {}
    for fname in NEEDED:
        path = UNIHAN_DIR / fname
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            code, field, value = parts
            if field not in wanted:
                continue
            ch = chr(int(code[2:], 16))  # 'U+xxxx'
            out.setdefault(S.nfc(ch), {})[field] = value
    return out


def radical_char(krsunicode):
    """kRSUnicode like '75.4' -> (radical char, residual strokes)."""
    try:
        rad, rest = krsunicode.split(" ")[0].split(".")
        rad_num = int(rad.rstrip("'"))  # trailing ' marks simplified radical
        return chr(_KANGXI_BASE + rad_num - 1), int(rest)
    except (ValueError, IndexError):
        return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=["core", "full"], default="core")
    args = ap.parse_args()

    ensure_unihan()
    uni = load_fields({"kDefinition", "kRSUnicode", "kTotalStrokes"})
    S.log(f"Unihan: {len(uni)} characters with requested fields")

    path = S.STAGING / "characters.jsonl"
    chars = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

    n_gloss = n_rad = n_strokes = 0
    for c in chars:
        u = uni.get(c["hanja"])
        if not u:
            continue
        if u.get("kDefinition"):
            # first gloss only, trimmed
            gloss = u["kDefinition"].split(";")[0].strip()
            if gloss and not c.get("meaning_en"):
                c["meaning_en"] = gloss
                n_gloss += 1
        if c.get("radical") is None and u.get("kRSUnicode"):
            rad, _ = radical_char(u["kRSUnicode"])
            if rad:
                c["radical"] = rad
                n_rad += 1
        if c.get("total_strokes") is None and u.get("kTotalStrokes"):
            try:
                c["total_strokes"] = int(u["kTotalStrokes"].split(" ")[0])
                n_strokes += 1
            except ValueError:
                pass

    with open(path, "w", encoding="utf-8") as f:
        for c in chars:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    S.log(f"enriched: +{n_gloss} English glosses, "
          f"backfilled {n_rad} radicals, {n_strokes} stroke counts")


if __name__ == "__main__":
    main()
