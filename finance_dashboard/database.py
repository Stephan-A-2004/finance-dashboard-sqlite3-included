"""Database operations."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any
from pathlib import Path

from finance_dashboard.config import DB_FILE


SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS queries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  source TEXT NOT NULL,
  input_text TEXT NOT NULL,
  tickers_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  query_id INTEGER NOT NULL,
  ticker TEXT NOT NULL,
  data_json TEXT NOT NULL,
  FOREIGN KEY(query_id) REFERENCES queries(id)
);

CREATE INDEX IF NOT EXISTS idx_results_query ON results(query_id);
CREATE INDEX IF NOT EXISTS idx_results_ticker ON results(ticker);
"""


def connect(db_path: Path = DB_FILE) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.executescript(SCHEMA_SQL)
    return conn


def insert_query(
    conn: sqlite3.Connection, source: str, input_text: str, tickers: list[str]
) -> int:
    created_at = datetime.now(timezone.utc).isoformat()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO queries(created_at, source, input_text, tickers_json) VALUES (?, ?, ?, ?)",
        (created_at, source, input_text, json.dumps(tickers)),
    )
    conn.commit()
    if cur.lastrowid is None:
        raise RuntimeError("Insert failed: cursor.lastrowid is None")
    return int(cur.lastrowid)


def insert_results(
    conn: sqlite3.Connection, query_id: int, rows: list[tuple[str, dict]]
) -> None:
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO results(query_id, ticker, data_json) VALUES (?, ?, ?)",
        [(query_id, t, json.dumps(d)) for (t, d) in rows],
    )
    conn.commit()


def list_queries(conn: sqlite3.Connection) -> list[tuple[int, str, str, str]]:
    cur = conn.cursor()
    cur.execute(
        "SELECT id, created_at, source, input_text FROM queries ORDER BY id DESC"
    )
    return cur.fetchall()


def load_query_results(
    conn: sqlite3.Connection, query_id: int
) -> tuple[list[str], list[dict]]:
    cur = conn.cursor()
    cur.execute("SELECT tickers_json FROM queries WHERE id=?", (query_id,))
    row = cur.fetchone()
    tickers = json.loads(row[0]) if row else []

    cur.execute(
        "SELECT ticker, data_json FROM results WHERE query_id=? ORDER BY ticker",
        (query_id,),
    )
    res = cur.fetchall()
    data_rows = []
    for ticker, data_json in res:
        d = json.loads(data_json)
        d["Ticker"] = ticker
        data_rows.append(d)
    return tickers, data_rows


def clear_all(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("DELETE FROM results")
    cur.execute("DELETE FROM queries")
    conn.commit()