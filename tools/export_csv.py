"""SQLite の内容を Excel で開ける CSV に書き出す。 使い方: python tools/export_csv.py"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import storage  # noqa: E402

# ===== [BLOCK: EXPORT] START =====
output_dir = ROOT / "var" / "export"
output_dir.mkdir(parents=True, exist_ok=True)
for table in ("diagnoses", "events", "leads"):
    columns, rows = storage.fetch_table(table)
    path = output_dir / f"{table}.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        writer.writerows(rows)
    print(f"{path}: {len(rows)}件")
# ===== [BLOCK: EXPORT] END =====
