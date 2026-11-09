"""SQLite への保存。本番では Firestore / Supabase などに置き換える層。"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ===== [BLOCK: CONFIG] START =====
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("HARMONIZE_DB_PATH", ROOT / "var" / "harmonize.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS diagnoses (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  quiz_version TEXT NOT NULL,
  type_code TEXT NOT NULL,
  axis_scores TEXT NOT NULL,
  answers TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  diagnosis_id TEXT NOT NULL REFERENCES diagnoses(id),
  name TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  diagnosis_id TEXT NOT NULL REFERENCES diagnoses(id),
  company TEXT NOT NULL,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""
# ===== [BLOCK: CONFIG] END =====


# ===== [BLOCK: CONNECTION] START =====
def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.executescript(SCHEMA)
    return connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
# ===== [BLOCK: CONNECTION] END =====


# ===== [BLOCK: WRITE_OPERATIONS] START =====
def save_diagnosis(
    diagnosis_id: str,
    quiz_version: str,
    type_code: str,
    axis_scores: dict[str, int],
    answers: dict[str, int],
) -> None:
    with closing(_connect()) as connection, connection:
        connection.execute(
            "INSERT INTO diagnoses VALUES (?, ?, ?, ?, ?, ?)",
            (
                diagnosis_id,
                _now(),
                quiz_version,
                type_code,
                json.dumps(axis_scores, ensure_ascii=False),
                json.dumps(answers, ensure_ascii=False),
            ),
        )


def save_event(diagnosis_id: str, name: str) -> None:
    with closing(_connect()) as connection, connection:
        connection.execute(
            "INSERT INTO events (diagnosis_id, name, created_at) VALUES (?, ?, ?)",
            (diagnosis_id, name, _now()),
        )


def save_lead(diagnosis_id: str, company: str, name: str, email: str) -> int:
    with closing(_connect()) as connection, connection:
        cursor = connection.execute(
            "INSERT INTO leads (diagnosis_id, company, name, email, created_at) VALUES (?, ?, ?, ?, ?)",
            (diagnosis_id, company, name, email, _now()),
        )
        return int(cursor.lastrowid)
# ===== [BLOCK: WRITE_OPERATIONS] END =====


# ===== [BLOCK: READ_FOR_EXPORT] START =====
def fetch_table(table: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    if table not in {"diagnoses", "events", "leads"}:
        raise ValueError(f"unknown table: {table}")
    with closing(_connect()) as connection:
        cursor = connection.execute(f"SELECT * FROM {table}")
        return [column[0] for column in cursor.description], cursor.fetchall()
# ===== [BLOCK: READ_FOR_EXPORT] END =====
