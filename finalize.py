#!/usr/bin/env python3
"""Re-fetch GitHub CSV (correct URL) and rebuild the report from cached parsed data.

The first explore.py run failed on the GitHub CSV (wrong URL in brief).
Rather than re-scrape stdict + krdict (slow), reload parsed JSON files and
rebuild only what's needed.
"""

import csv
import io
import json
from pathlib import Path

import requests

from explore import (
    TEST_CHARS,
    GITHUB_CSV_URL,
    analyze_github,
    build_report,
    RAW,
    PARSED,
    ROOT,
)


def fetch_github_csv():
    cached = RAW / "github" / "dataset.csv"
    if cached.exists():
        text = cached.read_text(encoding="utf-8")
    else:
        r = requests.get(GITHUB_CSV_URL, timeout=30)
        r.raise_for_status()
        text = r.text
        cached.write_text(text, encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    return rows, reader.fieldnames


def load_parsed(source):
    out = {}
    for c in TEST_CHARS:
        f = PARSED / source / f"{c['hanja']}.json"
        if f.exists():
            out[c["hanja"]] = json.loads(f.read_text(encoding="utf-8"))
        else:
            out[c["hanja"]] = {}
    return out


def main():
    rows, cols = fetch_github_csv()
    print(f"GitHub: {len(rows)} rows, columns={cols}")
    github_by_char = analyze_github(rows, cols)
    stdict_data = load_parsed("stdict")
    krdict_data = load_parsed("krdict")
    report = build_report(rows, cols, github_by_char, stdict_data, krdict_data)
    (ROOT / "exploration_report.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
