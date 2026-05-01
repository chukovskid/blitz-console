"""SQLite store for ICP profiles, runs, and credit log.

Single-file DB at PROJECT_ROOT/blitz.db. Tables created on import if missing.
"""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "blitz.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS icp_profiles (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT UNIQUE NOT NULL,
    filters_json  TEXT NOT NULL,        -- SearchFilters.to_dict()
    options_json  TEXT NOT NULL,        -- RunOptions.to_dict()
    created_at    REAL NOT NULL,
    updated_at    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    icp_id        INTEGER,
    icp_name      TEXT,
    filters_json  TEXT NOT NULL,
    options_json  TEXT NOT NULL,
    status        TEXT NOT NULL,        -- queued|running|done|error|cancelled
    started_at    REAL,
    finished_at   REAL,
    credits_used  INTEGER DEFAULT 0,
    leads_total   INTEGER DEFAULT 0,
    emails_found  INTEGER DEFAULT 0,
    raw_path      TEXT,
    enriched_path TEXT,
    csv_path      TEXT,
    log_path      TEXT,
    error         TEXT,
    pid           INTEGER,
    FOREIGN KEY(icp_id) REFERENCES icp_profiles(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS credit_log (
    ts            REAL NOT NULL,
    balance       INTEGER NOT NULL,
    note          TEXT
);

CREATE TABLE IF NOT EXISTS count_cache (
    filter_hash   TEXT PRIMARY KEY,
    total_results INTEGER NOT NULL,
    cached_at     REAL NOT NULL
);
"""


@contextmanager
def conn() -> Iterator[sqlite3.Connection]:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db() -> None:
    with conn() as c:
        c.executescript(SCHEMA)


# ---- ICP profiles ---------------------------------------------------------


def list_icps() -> list[dict]:
    with conn() as c:
        rows = c.execute(
            "SELECT id, name, created_at, updated_at FROM icp_profiles ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_icp(name: str) -> dict | None:
    with conn() as c:
        r = c.execute("SELECT * FROM icp_profiles WHERE name = ?", (name,)).fetchone()
    return dict(r) if r else None


def upsert_icp(name: str, filters_dict: dict, options_dict: dict) -> int:
    now = time.time()
    with conn() as c:
        existing = c.execute("SELECT id FROM icp_profiles WHERE name = ?", (name,)).fetchone()
        if existing:
            c.execute(
                "UPDATE icp_profiles SET filters_json=?, options_json=?, updated_at=? WHERE name=?",
                (json.dumps(filters_dict), json.dumps(options_dict), now, name),
            )
            return existing["id"]
        cur = c.execute(
            "INSERT INTO icp_profiles (name, filters_json, options_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (name, json.dumps(filters_dict), json.dumps(options_dict), now, now),
        )
        return cur.lastrowid


def delete_icp(name: str) -> None:
    with conn() as c:
        c.execute("DELETE FROM icp_profiles WHERE name = ?", (name,))


# ---- Runs -----------------------------------------------------------------


def create_run(
    icp_id: int | None,
    icp_name: str | None,
    filters_dict: dict,
    options_dict: dict,
    raw_path: str,
    enriched_path: str,
    csv_path: str,
    log_path: str,
) -> int:
    with conn() as c:
        cur = c.execute(
            "INSERT INTO runs (icp_id, icp_name, filters_json, options_json, status, "
            "raw_path, enriched_path, csv_path, log_path) VALUES (?, ?, ?, ?, 'queued', ?, ?, ?, ?)",
            (
                icp_id,
                icp_name,
                json.dumps(filters_dict),
                json.dumps(options_dict),
                raw_path,
                enriched_path,
                csv_path,
                log_path,
            ),
        )
        return cur.lastrowid


def update_run(run_id: int, **kwargs) -> None:
    if not kwargs:
        return
    cols = ", ".join(f"{k} = ?" for k in kwargs.keys())
    with conn() as c:
        c.execute(f"UPDATE runs SET {cols} WHERE id = ?", (*kwargs.values(), run_id))


def get_run(run_id: int) -> dict | None:
    with conn() as c:
        r = c.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    return dict(r) if r else None


def list_runs(limit: int = 50) -> list[dict]:
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ---- Credit log -----------------------------------------------------------


def log_balance(balance: int, note: str = "") -> None:
    with conn() as c:
        c.execute("INSERT INTO credit_log (ts, balance, note) VALUES (?, ?, ?)", (time.time(), balance, note))


def credit_history(limit: int = 200) -> list[dict]:
    with conn() as c:
        rows = c.execute(
            "SELECT ts, balance, note FROM credit_log ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ---- Count cache ----------------------------------------------------------


def cache_count(filter_hash: str, total: int) -> None:
    with conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO count_cache (filter_hash, total_results, cached_at) VALUES (?, ?, ?)",
            (filter_hash, total, time.time()),
        )


def get_cached_count(filter_hash: str, max_age_s: int = 86400) -> int | None:
    with conn() as c:
        r = c.execute(
            "SELECT total_results, cached_at FROM count_cache WHERE filter_hash = ?",
            (filter_hash,),
        ).fetchone()
    if not r:
        return None
    if time.time() - r["cached_at"] > max_age_s:
        return None
    return r["total_results"]


# initialize on import
init_db()
