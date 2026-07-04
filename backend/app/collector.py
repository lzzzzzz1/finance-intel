from __future__ import annotations

import json
import sqlite3
from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover - optional until dependencies install
    httpx = None

from .analyzer import analyze_with_openai
from .extract import clean_html, extract_tickers, match_themes, raw_hash, utc_now_iso


def source_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM sources WHERE enabled = 1 ORDER BY region, category, name").fetchall()
    return [dict(row) for row in rows]


def theme_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT name, keywords FROM themes WHERE enabled = 1 ORDER BY name").fetchall()
    themes = []
    for row in rows:
        try:
            keywords = json.loads(row["keywords"])
        except json.JSONDecodeError:
            keywords = []
        themes.append({"name": row["name"], "keywords": keywords})
    return themes


def collect_all(conn: sqlite3.Connection, settings) -> dict[str, int]:
    inserted = 0
    failed = 0
    themes = theme_rows(conn)
    for source in source_rows(conn):
        try:
            events = fetch_source(source, settings.user_agent)
            for event in events:
                event["tickers"] = extract_tickers(f"{event['title']} {event['body']}")
                event["themes"] = match_themes(f"{event['title']} {event['body']}", themes)
                if save_event_with_analysis(conn, event, settings):
                    inserted += 1
            mark_source_status(conn, source["id"], "ok", "")
        except Exception as exc:
            failed += 1
            mark_source_status(conn, source["id"], "failed", str(exc)[:500])
    conn.commit()
    return {"inserted": inserted, "failed": failed}


def fetch_source(source: dict[str, Any], user_agent: str) -> list[dict[str, Any]]:
    if httpx is None:
        return [offline_placeholder(source, "依赖尚未安装，显示来源配置占位事件。")]

    headers = {"User-Agent": user_agent}
    with httpx.Client(timeout=12, follow_redirects=True, headers=headers) as client:
        response = client.get(source["url"])
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "json" in content_type or source["id"] == "sec_edgar":
            return parse_json_source(source, response.text)
        return parse_html_source(source, response.text)


def parse_html_source(source: dict[str, Any], html: str) -> list[dict[str, Any]]:
    text = clean_html(html)
    title = f"{source['name']}最新公开信息"
    body = text[:6000] or "该来源暂无可抽取正文，请打开原文查看。"
    return [event_payload(source, title, body, source["url"])]


def parse_json_source(source: dict[str, Any], payload: str) -> list[dict[str, Any]]:
    data = json.loads(payload)
    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    dates = filings.get("filingDate", [])
    accession = filings.get("accessionNumber", [])
    if not forms:
        return [event_payload(source, f"{source['name']}最新 JSON 数据", json.dumps(data, ensure_ascii=False)[:6000], source["url"])]
    events = []
    for index, form in enumerate(forms[:5]):
        filed = dates[index] if index < len(dates) else None
        acc = accession[index] if index < len(accession) else ""
        title = f"SEC filing {form} {filed or ''}".strip()
        body = f"SEC EDGAR filing form={form}, filingDate={filed}, accessionNumber={acc}."
        events.append(event_payload(source, title, body, source["url"], filed))
    return events


def offline_placeholder(source: dict[str, Any], reason: str) -> dict[str, Any]:
    return event_payload(source, f"{source['name']}来源已配置", reason, source["url"])


def event_payload(source: dict[str, Any], title: str, body: str, url: str, published_at: str | None = None) -> dict[str, Any]:
    payload = {
        "source_id": source["id"],
        "source_name": source["name"],
        "source_url": url,
        "title": title,
        "body": body,
        "published_at": published_at or utc_now_iso(),
        "category": source["category"],
        "region": source["region"],
        "trust_level": source["trust_level"],
    }
    payload["raw_hash"] = raw_hash(source["id"], title, body, url)
    return payload


def save_event_with_analysis(conn: sqlite3.Connection, event: dict[str, Any], settings) -> bool:
    try:
        cursor = conn.execute(
            """
            INSERT INTO events
            (source_id, source_name, source_url, title, body, published_at, category, region, raw_hash, tickers, themes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["source_id"],
                event["source_name"],
                event["source_url"],
                event["title"],
                event["body"],
                event["published_at"],
                event["category"],
                event["region"],
                event["raw_hash"],
                json.dumps(event.get("tickers", []), ensure_ascii=False),
                json.dumps(event.get("themes", []), ensure_ascii=False),
            ),
        )
    except sqlite3.IntegrityError:
        return False

    event_id = cursor.lastrowid
    api_key = get_setting(conn, "openai_api_key") or settings.openai_api_key
    analysis = analyze_with_openai(event, api_key=api_key, model=settings.openai_model).as_dict()
    conn.execute(
        """
        INSERT INTO analyses
        (event_id, summary, novice_explanation, importance_score, sentiment_score, risk_score,
         confidence_score, key_numbers, caveats, model, disclaimer)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            analysis["summary"],
            analysis["novice_explanation"],
            analysis["importance_score"],
            analysis["sentiment_score"],
            analysis["risk_score"],
            analysis["confidence_score"],
            json.dumps(analysis["key_numbers"], ensure_ascii=False),
            json.dumps(analysis["caveats"], ensure_ascii=False),
            analysis["model"],
            analysis["disclaimer"],
        ),
    )
    return True


def mark_source_status(conn: sqlite3.Connection, source_id: str, status: str, error: str) -> None:
    conn.execute(
        "UPDATE sources SET last_status = ?, last_error = ?, last_checked_at = ? WHERE id = ?",
        (status, error, utc_now_iso(), source_id),
    )


def get_setting(conn: sqlite3.Connection, key: str) -> str:
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else ""
