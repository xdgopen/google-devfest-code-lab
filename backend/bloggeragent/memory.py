"""Two-layer memory for the Blogger agent.

1. Profile memory – ADK `user:` scoped state. It is shared by every session of
   the same user and persisted by the session service (Postgres / Cloud SQL),
   so preferences and post history survive restarts and new chats.
     - user:preferences  {tone, audience, length, language}
     - user:post_history [{topic, slug, title, words, date, session_id}, ...]
2. Long-term semantic memory – ADK MemoryService. `preload_memory` injects
   relevant past conversations into each turn; the root agent's
   after_agent_callback stores every finished session. In-memory locally,
   Vertex AI Memory Bank on GCP (MEMORY_SERVICE_URI=agentengine://<id>).
"""

from __future__ import annotations

import datetime
import re

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import ToolContext

from .logging_utils import get_logger, log_event

PREFS_KEY = "user:preferences"
HISTORY_KEY = "user:post_history"
MAX_HISTORY = 20
PREF_FIELDS = ("tone", "audience", "length", "language")
_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def merge_preferences(current: dict | None, updates: dict) -> dict:
    merged = dict(current or {})
    for key in PREF_FIELDS:
        value = updates.get(key)
        if isinstance(value, str) and value.strip():
            merged[key] = value.strip()[:80]
    return merged


def apply_preferences_to_session(state, prefs: dict) -> None:
    """Session-level values (sent by the UI) win; memory fills the gaps."""
    for key in PREF_FIELDS:
        if not state.get(key) and prefs.get(key):
            state[key] = prefs[key]


def build_history_entry(state: dict, session_id: str, today: str | None = None) -> dict | None:
    post = state.get("blog_post")
    if not post:
        return None
    title_match = _TITLE_RE.search(post)
    seo = state.get("blog_seo") or {}
    stats = state.get("blog_stats") or {}
    return {
        "session_id": session_id,
        "topic": state.get("blog_topic") or (title_match.group(1) if title_match else ""),
        "title": title_match.group(1).strip() if title_match else "",
        "slug": seo.get("slug", ""),
        "words": stats.get("word_count"),
        "date": today or datetime.date.today().isoformat(),
    }


def append_history(history: list | None, entry: dict) -> list:
    items = [h for h in (history or []) if h.get("session_id") != entry["session_id"]]
    items.append(entry)
    return items[-MAX_HISTORY:]


# ---------------------------- tools ---------------------------------------- #
def remember_preferences(
    tool_context: ToolContext,
    tone: str = "",
    audience: str = "",
    length: str = "",
    language: str = "",
) -> dict:
    """Saves the user's writing preferences for all future sessions.

    Call this when the user states a lasting preference (e.g. "always write in
    Vietnamese", "my readers are beginners").

    Args:
      tone: e.g. "friendly", "formal".
      audience: e.g. "senior backend engineers".
      length: e.g. "short (~800 words)".
      language: e.g. "Vietnamese".
    """
    prefs = merge_preferences(
        tool_context.state.get(PREFS_KEY),
        {"tone": tone, "audience": audience, "length": length, "language": language},
    )
    tool_context.state[PREFS_KEY] = prefs
    for key, value in prefs.items():
        tool_context.state[key] = value
    return {"status": "saved", "preferences": prefs}


def recall_past_posts(tool_context: ToolContext, limit: int = 5) -> dict:
    """Lists the user's most recent blog posts (to avoid repeats / link them).

    Args:
      limit: how many recent posts to return (1-20).
    """
    history = tool_context.state.get(HISTORY_KEY) or []
    limit = max(1, min(int(limit or 5), MAX_HISTORY))
    return {"count": len(history), "posts": list(reversed(history))[:limit]}


# ---------------------------- callbacks ------------------------------------ #
def load_profile_memory(callback_context: CallbackContext) -> object | None:
    """before_agent_callback (root): hydrate session prefs from user memory."""
    prefs = callback_context.state.get(PREFS_KEY) or {}
    if prefs:
        apply_preferences_to_session(callback_context.state, prefs)
    return None


async def save_memories(callback_context: CallbackContext) -> None:
    """after_agent_callback (root): update post history + long-term memory."""
    state = callback_context.state
    session = callback_context._invocation_context.session
    entry = build_history_entry(state.to_dict(), session.id)
    if entry:
        state[HISTORY_KEY] = append_history(state.get(HISTORY_KEY), entry)
    try:
        await callback_context.add_session_to_memory()
    except ValueError:
        pass  # no memory service configured (e.g. plain unit tests)
    except Exception as exc:  # pragma: no cover - remote service failure
        log_event(get_logger(), "memory_save_failed", error=str(exc))
    return None
