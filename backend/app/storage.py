from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .sources import DEFAULT_THEMES, TRUSTED_SOURCES


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            region TEXT NOT NULL,
            url TEXT NOT NULL,
            trust_level TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            last_status TEXT,
            last_error TEXT,
            last_checked_at TEXT
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL REFERENCES sources(id),
            source_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            published_at TEXT,
            category TEXT NOT NULL,
            region TEXT NOT NULL,
            raw_hash TEXT NOT NULL UNIQUE,
            tickers TEXT NOT NULL DEFAULT '[]',
            themes TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS analyses (
            event_id INTEGER PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
            summary TEXT NOT NULL,
            novice_explanation TEXT NOT NULL,
            importance_score INTEGER NOT NULL,
            sentiment_score INTEGER NOT NULL,
            risk_score INTEGER NOT NULL,
            confidence_score INTEGER NOT NULL,
            key_numbers TEXT NOT NULL DEFAULT '[]',
            caveats TEXT NOT NULL DEFAULT '[]',
            model TEXT NOT NULL,
            disclaimer TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            market TEXT NOT NULL DEFAULT 'CN',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS themes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            keywords TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    seed_defaults(conn)
    conn.commit()


def seed_defaults(conn: sqlite3.Connection) -> None:
    for source in TRUSTED_SOURCES:
        conn.execute(
            """
            INSERT OR IGNORE INTO sources
            (id, name, category, region, url, trust_level, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (source.id, source.name, source.category, source.region, source.url, source.trust_level, int(source.enabled_default)),
        )
    for theme in DEFAULT_THEMES:
        conn.execute(
            "INSERT OR IGNORE INTO themes (name, keywords, enabled) VALUES (?, ?, 1)",
            (theme["name"], json.dumps(theme["keywords"], ensure_ascii=False)),
        )
    conn.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES ('collect_interval_minutes', '180')")
    conn.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES ('openai_api_key', '')")


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    for key in ("tickers", "themes", "key_numbers", "caveats", "keywords"):
        if key in data and isinstance(data[key], str):
            try:
                data[key] = json.loads(data[key])
            except json.JSONDecodeError:
                data[key] = []
    return data


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [row_to_dict(row) for row in rows if row is not None]
