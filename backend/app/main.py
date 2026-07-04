from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router
from .collector import collect_all
from .config import PROJECT_DIR, get_settings
from .storage import connect, init_db


settings = get_settings()
scheduler = BackgroundScheduler(timezone="UTC")


def scheduled_collect() -> None:
    conn = connect(settings.database_path)
    try:
        init_db(conn)
        collect_all(conn, settings)
    finally:
        conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = connect(settings.database_path)
    try:
        init_db(conn)
    finally:
        conn.close()

    if not scheduler.running:
        scheduler.add_job(
            scheduled_collect,
            "interval",
            minutes=settings.collect_interval_minutes,
            id="collect-trusted-sources",
            replace_existing=True,
        )
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="Local Finance Intelligence",
    description="可信公开来源聚合、提炼和量化评分。本工具不构成投资建议。",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

frontend_dist = PROJECT_DIR / "frontend" / "dist"
assets_dir = frontend_dist / "assets"

if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/")
def root():
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"name": "Local Finance Intelligence", "api": "/api/dashboard", "disclaimer": "not investment advice"}


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    path = Path(full_path)
    if path.parts and path.parts[0] == "api":
        raise HTTPException(status_code=404, detail="not found")
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"name": "Local Finance Intelligence", "api": "/api/dashboard"}
