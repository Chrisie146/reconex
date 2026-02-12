"""Debug helper to run the CSV normalizer on a given file and print results.

Usage:
  venv\Scripts\python backend\tools\debug_parse.py ../62514285346.csv

This script imports the project's `services.parser.normalize_csv` to reproduce parsing behavior.
"""
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.parser import normalize_csv


def main():
    if len(sys.argv) < 2:
        print("Usage: python backend/tools/debug_parse.py <csv-file>")
        return

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"File not found: {csv_path}")
        return

    with open(csv_path, "rb") as f:
        content = f.read()

    txns, summary_warnings, skipped = normalize_csv(content)

    print(f"Parsed transactions: {len(txns)}")
    print(f"Summary warnings: {summary_warnings}")
    if skipped:
        print(f"Skipped rows: {len(skipped)}")
        for s in skipped[:50]:
            print(s)
    else:
        print("No skipped rows")


if __name__ == '__main__':
    main()
