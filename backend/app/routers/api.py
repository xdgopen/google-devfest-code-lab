"""Public JSON + SSE API used by the React UI."""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import PlainTextResponse, Response, StreamingResponse
from google.genai import types
from pydantic import BaseModel, Field

from bloggeragent.memory import HISTORY_KEY, PREFS_KEY
from bloggeragent.tools.seo import slugify

from ..export import to_html_document
from ..progress import event_to_messages, session_detail, summarize_session
from ..services import AppServices

router = APIRouter(prefix="/api", tags=["blogger"])

USER_ID = Path(..., pattern=r"^[A-Za-z0-9_-]{1,64}$")
_ALLOWED_PREFS = ("tone", "audience", "length", "language")


def get_services(request: Request) -> AppServices:
    return request.app.state.services


class Preferences(BaseModel):
    tone: str | None = Field(default=None, max_length=80)
    audience: str | None = Field(default=None, max_length=80)
    length: str | None = Field(default=None, max_length=80)
    language: str | None = Field(default=None, max_length=40)


class CreateSession(BaseModel):
    preferences: Preferences = Field(default_factory=Preferences)


class RunRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=20000)


async def _get_session_or_404(svc: AppServices, user_id: str, session_id: str):
    session = await svc.sessions.get_session(
        app_name=svc.app_name, user_id=user_id, session_id=session_id
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/config")
async def config(svc: AppServices = Depends(get_services)) -> dict:
    s = svc.settings
    return {
        "app_name": s.app_name,
        "model": s.model,
        "auth_mode": s.auth_mode,
        "features": {
            "research": s.enable_research,
            "memory": s.enable_memory,
            "persistent_sessions": bool(s.database_url),
            "artifact_bucket": bool(s.artifact_bucket),
        },
        "limits": {"max_input_chars": s.max_input_chars, "max_loop_iterations": s.max_loop_iterations},
    }


@router.post("/users/{user_id}/sessions", status_code=201)
async def create_session(
    body: CreateSession, user_id: str = USER_ID, svc: AppServices = Depends(get_services)
) -> dict:
    state = {k: v for k, v in body.preferences.model_dump().items() if v}
    session = await svc.sessions.create_session(
        app_name=svc.app_name, user_id=user_id, state=state
    )
    return {"session_id": session.id, "state": {k: session.state.get(k) for k in state}}


def _sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


@router.post("/users/{user_id}/sessions/{session_id}/run")
async def run(
    body: RunRequest,
    session_id: str,
    user_id: str = USER_ID,
    svc: AppServices = Depends(get_services),
):
    """Runs the agent and streams progress as Server-Sent Events."""
    await _get_session_or_404(svc, user_id, session_id)
    message = types.Content(role="user", parts=[types.Part(text=body.message)])

    async def stream() -> AsyncIterator[str]:
        yield _sse({"type": "run_started", "session_id": session_id})
        try:
            async for event in svc.runner.run_async(
                user_id=user_id, session_id=session_id, new_message=message
            ):
                for msg in event_to_messages(event):
                    yield _sse(msg)
        except Exception as exc:  # surface model/API errors to the UI
            yield _sse({"type": "error", "error": f"{type(exc).__name__}: {exc}"[:500]})
            return
        session = await svc.sessions.get_session(
            app_name=svc.app_name, user_id=user_id, session_id=session_id
        )
        yield _sse({"type": "done", "result": session_detail(session)})

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/users/{user_id}/blogs")
async def list_blogs(
    user_id: str = USER_ID,
    limit: int = Query(20, ge=1, le=100),
    svc: AppServices = Depends(get_services),
) -> dict:
    listed = await svc.sessions.list_sessions(app_name=svc.app_name, user_id=user_id)
    items = []
    for s in sorted(listed.sessions, key=lambda s: s.last_update_time, reverse=True)[:limit]:
        full = await svc.sessions.get_session(app_name=svc.app_name, user_id=user_id, session_id=s.id)
        if full and full.events:
            items.append(summarize_session(full))
    return {"items": items}


@router.get("/users/{user_id}/blogs/{session_id}")
async def get_blog(session_id: str, user_id: str = USER_ID, svc: AppServices = Depends(get_services)) -> dict:
    return session_detail(await _get_session_or_404(svc, user_id, session_id))


@router.delete("/users/{user_id}/blogs/{session_id}", status_code=204)
async def delete_blog(session_id: str, user_id: str = USER_ID, svc: AppServices = Depends(get_services)):
    await _get_session_or_404(svc, user_id, session_id)
    await svc.sessions.delete_session(app_name=svc.app_name, user_id=user_id, session_id=session_id)
    return Response(status_code=204)


@router.get("/users/{user_id}/blogs/{session_id}/export")
async def export_blog(
    session_id: str,
    user_id: str = USER_ID,
    format: str = Query("md", pattern="^(md|html)$"),
    svc: AppServices = Depends(get_services),
):
    detail = session_detail(await _get_session_or_404(svc, user_id, session_id))
    if not detail["post"]:
        raise HTTPException(status_code=404, detail="This session has no blog post yet")
    filename = (detail["seo"].get("slug") or slugify(detail["title"]) or "blog-post")
    if format == "md":
        return PlainTextResponse(
            detail["post"], media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}.md"'},
        )
    lang = "vi" if re.match(r"(?i)^(vi|vietnamese|tiếng việt)", detail["preferences"].get("language", "")) else "en"
    doc = to_html_document(detail["post"], detail["title"], detail["seo"].get("meta_description", ""), lang)
    return Response(
        doc, media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}.html"'},
    )


@router.get("/users/{user_id}/memory")
async def get_memory(user_id: str = USER_ID, svc: AppServices = Depends(get_services)) -> dict:
    """Profile memory (user: scoped state) – preferences + post history."""
    state = await svc.sessions.get_user_state(app_name=svc.app_name, user_id=user_id)
    return {
        "preferences": state.get(PREFS_KEY.removeprefix("user:")) or state.get(PREFS_KEY) or {},
        "post_history": list(reversed(state.get(HISTORY_KEY.removeprefix("user:")) or state.get(HISTORY_KEY) or [])),
    }
