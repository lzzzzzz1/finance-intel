from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from .analyzer import build_reading_sections, extract_evidence_snippets
from .collector import collect_all
from .config import Settings, get_settings
from .storage import connect, init_db, row_to_dict, rows_to_dicts


router = APIRouter(prefix="/api")


class WatchItem(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=80)
    market: str = "CN"
    notes: str = ""


class ThemeInput(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    keywords: list[str] = Field(default_factory=list)
    enabled: bool = True


class SettingsInput(BaseModel):
    collect_interval_minutes: int = Field(ge=15, le=1440)
    openai_api_key: str = ""


def db_path(settings: Settings = Depends(get_settings)) -> Path:
    return settings.database_path


def get_conn(path: Path = Depends(db_path)):
    conn = connect(path)
    init_db(conn)
    try:
        yield conn
    finally:
        conn.close()


def require_admin(
    x_admin_token: str = Header(default=""),
    settings: Settings = Depends(get_settings),
) -> None:
    if settings.admin_token and x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="admin token required")


@router.get("/dashboard")
def dashboard(conn=Depends(get_conn)) -> dict[str, Any]:
    events = rows_to_dicts(
        conn.execute(
            """
            SELECT e.*, a.summary, a.novice_explanation, a.importance_score, a.sentiment_score,
                   a.risk_score, a.confidence_score, a.key_numbers, a.caveats, a.model, a.disclaimer
            FROM events e
            JOIN analyses a ON a.event_id = e.id
            ORDER BY a.importance_score DESC, e.published_at DESC
            LIMIT 60
            """
        ).fetchall()
    )
    events = enrich_events(events)
    sources = rows_to_dicts(conn.execute("SELECT * FROM sources ORDER BY region, category, name").fetchall())
    return {
        "events": events,
        "sources": sources,
        "stats": {
            "event_count": conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"],
            "watch_count": conn.execute("SELECT COUNT(*) AS c FROM watchlist").fetchone()["c"],
            "theme_count": conn.execute("SELECT COUNT(*) AS c FROM themes WHERE enabled = 1").fetchone()["c"],
        },
    }


@router.get("/events/{event_id}")
def event_detail(event_id: int, conn=Depends(get_conn)) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT e.*, a.summary, a.novice_explanation, a.importance_score, a.sentiment_score,
               a.risk_score, a.confidence_score, a.key_numbers, a.caveats, a.model, a.disclaimer
        FROM events e
        JOIN analyses a ON a.event_id = e.id
        WHERE e.id = ?
        """,
        (event_id,),
    ).fetchone()
    event = row_to_dict(row)
    if not event:
        raise HTTPException(status_code=404, detail="event not found")
    return enrich_event(event)


@router.get("/themes")
def list_themes(conn=Depends(get_conn)) -> list[dict[str, Any]]:
    return rows_to_dicts(conn.execute("SELECT * FROM themes ORDER BY name").fetchall())


@router.post("/themes")
def upsert_theme(item: ThemeInput, conn=Depends(get_conn), _: None = Depends(require_admin)) -> dict[str, Any]:
    conn.execute(
        """
        INSERT INTO themes (name, keywords, enabled)
        VALUES (?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET keywords = excluded.keywords, enabled = excluded.enabled
        """,
        (item.name, json.dumps(item.keywords, ensure_ascii=False), int(item.enabled)),
    )
    conn.commit()
    return {"ok": True}


@router.get("/watchlist")
def watchlist(conn=Depends(get_conn)) -> list[dict[str, Any]]:
    return rows_to_dicts(conn.execute("SELECT * FROM watchlist ORDER BY created_at DESC").fetchall())


@router.post("/watchlist")
def add_watch(item: WatchItem, conn=Depends(get_conn), _: None = Depends(require_admin)) -> dict[str, Any]:
    conn.execute(
        """
        INSERT INTO watchlist (ticker, name, market, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(ticker) DO UPDATE SET name = excluded.name, market = excluded.market, notes = excluded.notes
        """,
        (item.ticker.upper(), item.name, item.market.upper(), item.notes),
    )
    conn.commit()
    return {"ok": True}


@router.delete("/watchlist/{ticker}")
def remove_watch(ticker: str, conn=Depends(get_conn), _: None = Depends(require_admin)) -> dict[str, Any]:
    conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper(),))
    conn.commit()
    return {"ok": True}


@router.get("/settings")
def settings(conn=Depends(get_conn)) -> dict[str, Any]:
    rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
    data = {row["key"]: row["value"] for row in rows}
    data["openai_api_key"] = "configured" if data.get("openai_api_key") else ""
    return data


@router.put("/settings")
def update_settings(payload: SettingsInput, conn=Depends(get_conn), _: None = Depends(require_admin)) -> dict[str, Any]:
    conn.execute(
        "INSERT INTO app_settings (key, value) VALUES ('collect_interval_minutes', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(payload.collect_interval_minutes),),
    )
    if payload.openai_api_key:
        conn.execute(
            "INSERT INTO app_settings (key, value) VALUES ('openai_api_key', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (payload.openai_api_key,),
        )
    conn.commit()
    return {"ok": True}


@router.post("/refresh")
def refresh(
    conn=Depends(get_conn),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_admin),
) -> dict[str, int]:
    return collect_all(conn, settings)


def enrich_event(event: dict[str, Any] | None) -> dict[str, Any] | None:
    if not event:
        return event
    body = event.get("body", "")
    event["reading_sections"] = build_reading_sections(body)
    event["evidence_snippets"] = extract_evidence_snippets(body, event.get("title", ""), event.get("key_numbers", []))
    return event


def enrich_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [enrich_event(event) for event in events]
