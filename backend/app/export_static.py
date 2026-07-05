from __future__ import annotations

import argparse
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .collector import collect_all
from .config import get_settings
from .api import enrich_events
from .storage import connect, init_db, rows_to_dicts


def build_dashboard(conn) -> dict:
    events = rows_to_dicts(
        conn.execute(
            """
            SELECT e.*, a.summary, a.novice_explanation, a.importance_score, a.sentiment_score,
                   a.risk_score, a.confidence_score, a.key_numbers, a.caveats, a.model, a.disclaimer
            FROM events e
            JOIN analyses a ON a.event_id = e.id
            ORDER BY a.importance_score DESC, e.published_at DESC
            LIMIT 80
            """
        ).fetchall()
    )
    events = enrich_events(events)
    sources = rows_to_dicts(conn.execute("SELECT * FROM sources ORDER BY region, category, name").fetchall())
    themes = rows_to_dicts(conn.execute("SELECT * FROM themes ORDER BY name").fetchall())
    watchlist = rows_to_dicts(conn.execute("SELECT * FROM watchlist ORDER BY created_at DESC").fetchall())
    return {
        "events": events,
        "sources": sources,
        "themes": themes,
        "watchlist": watchlist,
        "stats": {
            "event_count": conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"],
            "watch_count": conn.execute("SELECT COUNT(*) AS c FROM watchlist").fetchone()["c"],
            "theme_count": conn.execute("SELECT COUNT(*) AS c FROM themes WHERE enabled = 1").fetchone()["c"],
        },
    }


def export_static(output_path: Path, skip_collect: bool = False) -> dict:
    settings = get_settings()
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "static-export.db"
        conn = connect(db_path)
        try:
            init_db(conn)
            result = {"inserted": 0, "failed": 0}
            if not skip_collect:
                result = collect_all(conn, settings)
            dashboard = build_dashboard(conn)
            dashboard["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            dashboard["collect_result"] = result
        finally:
            conn.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Export dashboard data for static hosting.")
    parser.add_argument("--output", default="frontend/public/data/dashboard.json")
    parser.add_argument("--skip-collect", action="store_true")
    args = parser.parse_args()
    result = export_static(Path(args.output), skip_collect=args.skip_collect)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
