from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(request: Request):
    services = request.app.state.services
    try:
        await services.sessions.list_sessions(app_name=services.app_name, user_id="__readyz__")
    except Exception as exc:  # DB unreachable etc.
        return JSONResponse({"status": "unavailable", "error": type(exc).__name__}, status_code=503)
    return {"status": "ready"}
