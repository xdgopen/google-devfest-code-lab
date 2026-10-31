"""FastAPI entrypoint: Blogger API + React SPA (+ optional ADK dev UI)."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from bloggeragent.config import Settings
from bloggeragent.logging_utils import get_logger

from .routers import api, health
from .services import AppServices, build_services

load_dotenv()

DEFAULT_STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


def create_app(
    settings: Settings | None = None,
    services: AppServices | None = None,
    static_dir: Path | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    get_logger(settings.log_level)
    services = services or build_services(settings)
    static_dir = static_dir or DEFAULT_STATIC_DIR

    app = FastAPI(title="Blogger Agent API", version="1.0.0")
    app.state.services = services
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(api.router)

    index = static_dir / "index.html"
    if index.exists():
        assets = static_dir / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa(full_path: str):
            candidate = (static_dir / full_path).resolve()
            if full_path and candidate.is_file() and static_dir.resolve() in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(index)

    return app


app = create_app()
