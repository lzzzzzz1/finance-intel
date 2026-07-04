from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional until dependencies install
    load_dotenv = None


ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = ROOT_DIR.parent

if load_dotenv:
    load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    database_path: Path
    collect_interval_minutes: int
    openai_api_key: str
    openai_model: str
    user_agent: str
    admin_token: str
    cors_origins: list[str]


def get_settings() -> Settings:
    db_path = os.getenv("DATABASE_PATH", str(PROJECT_DIR / "backend" / "data" / "intel.db"))
    cors_origins = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if origin.strip()
    ]
    return Settings(
        database_path=Path(db_path),
        collect_interval_minutes=int(os.getenv("COLLECT_INTERVAL_MINUTES", "180")),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        user_agent=os.getenv("USER_AGENT", "LocalFinanceIntel/0.1 contact=local"),
        admin_token=os.getenv("ADMIN_TOKEN", ""),
        cors_origins=cors_origins,
    )
