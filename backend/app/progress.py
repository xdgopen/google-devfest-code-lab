"""Translate raw ADK events into small UI progress messages (pure functions)."""

from __future__ import annotations

from typing import Any

from google.adk.events import Event

# Root-level tool → user-facing pipeline step
STEP_FOR_TOOL = {
    "Researcher": "research",
    "fetch_repo_context": "context",
    "RobustBlogPlanner": "plan",
    "RobustBlogWriter": "write",
    "seo_suggestions": "seo",
    "text_stats": "seo",
    "remember_preferences": "memory",
    "recall_past_posts": "memory",
    "preload_memory": "memory",
}
STEPS = ["research", "context", "plan", "write", "seo", "done"]
SHARED_STATE_KEYS = ("blog_outline", "blog_post", "blog_seo", "blog_stats", "loop_iterations")


def event_to_messages(event: Event) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    author = event.author
    if event.content and event.content.parts:
        for part in event.content.parts:
            if part.function_call:
                name = part.function_call.name
                messages.append({"type": "step_started", "author": author, "tool": name,
                                 "step": STEP_FOR_TOOL.get(name, "tool")})
            elif part.function_response:
                name = part.function_response.name
                response = part.function_response.response or {}
                ok = not (isinstance(response, dict) and response.get("status") == "error"
                          or isinstance(response, dict) and "error" in response)
                messages.append({"type": "step_finished", "author": author, "tool": name,
                                 "step": STEP_FOR_TOOL.get(name, "tool"), "ok": ok,
                                 "error": response.get("error") if not ok else None})
            elif part.text and not part.thought and not event.partial:
                messages.append({"type": "message", "author": author, "text": part.text})
    delta = event.actions.state_delta if event.actions else None
    if delta:
        shared = {k: delta[k] for k in SHARED_STATE_KEYS if k in delta}
        if shared:
            messages.append({"type": "state", "values": shared})
        if delta.get("guardrail_blocked"):
            messages.append({"type": "blocked", "reason": delta.get("guardrail_reason", "")})
    return messages


def final_text(events: list[Event], root_name: str = "Blogger") -> str:
    for event in reversed(events):
        if event.author == root_name and event.content and event.content.parts:
            text = "".join(p.text or "" for p in event.content.parts if not p.thought)
            if text.strip():
                return text
    return ""


def summarize_session(session, root_name: str = "Blogger") -> dict[str, Any]:
    state = session.state or {}
    post = state.get("blog_post") or ""
    title = ""
    for line in post.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    first_user = ""
    for event in session.events:
        if event.author == "user" and event.content and event.content.parts:
            first_user = "".join(p.text or "" for p in event.content.parts)
            break
    return {
        "session_id": session.id,
        "title": title or first_user[:80] or "Untitled",
        "topic": state.get("blog_topic") or first_user,
        "has_post": bool(post),
        "words": (state.get("blog_stats") or {}).get("word_count"),
        "updated_at": session.last_update_time,
        "preferences": {k: state.get(k) for k in ("tone", "audience", "length", "language") if state.get(k)},
    }


def session_detail(session, root_name: str = "Blogger") -> dict[str, Any]:
    state = session.state or {}
    return {
        **summarize_session(session, root_name),
        "outline": state.get("blog_outline") or "",
        "post": state.get("blog_post") or "",
        "seo": state.get("blog_seo") or {},
        "stats": state.get("blog_stats") or {},
        "loop_iterations": state.get("loop_iterations") or {},
        "final": final_text(session.events, root_name),
        "blocked": bool(state.get("guardrail_blocked")),
    }
