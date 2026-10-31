from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# Never hit a real model or GCP from unit tests.
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.pop("GOOGLE_GENAI_USE_VERTEXAI", None)

from google.adk.artifacts import InMemoryArtifactService  # noqa: E402
from google.adk.memory import InMemoryMemoryService  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from bloggeragent.agent import build_root_agent  # noqa: E402
from bloggeragent.config import Settings  # noqa: E402
from tests.fakes import FakeLlm  # noqa: E402

ENV_KEYS = [
    "MODEL", "GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION",
    "ENABLE_RESEARCH", "MAX_LOOP_ITERATIONS", "MAX_INPUT_CHARS", "DATABASE_URL",
    "ARTIFACT_BUCKET", "ENABLE_ADK_WEB", "ALLOWED_ORIGINS", "LOG_LEVEL",
    "ENABLE_MEMORY", "MEMORY_SERVICE_URI", "MAX_TOOL_CALLS", "BLOCKED_TOPICS",
    "REDACT_PII", "SAFETY_THRESHOLD",
]


@pytest.fixture
def clean_env(monkeypatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


async def run_pipeline(
    verdicts: dict | None = None,
    settings: Settings | None = None,
    prompt: str = "How to build an AI agent using planning loops",
    initial_state: dict | None = None,
    sessions=None,
    memory_service=None,
    user_id: str = "u1",
    fake=None,
):
    """Runs the full agent tree with FakeLlm; returns (fake, events, session, artifacts)."""
    fake = fake or FakeLlm(verdicts=verdicts or {})
    agent = build_root_agent(settings or Settings(), model=fake)
    sessions = sessions or InMemorySessionService()
    artifacts = InMemoryArtifactService()
    memory_service = memory_service or InMemoryMemoryService()
    runner = Runner(
        app_name="bloggeragent", agent=agent, session_service=sessions,
        artifact_service=artifacts, memory_service=memory_service,
    )
    session = await sessions.create_session(
        app_name="bloggeragent", user_id=user_id, state=initial_state or {}
    )
    events = []
    async for event in runner.run_async(
        user_id=user_id, session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
    ):
        events.append(event)
    session = await sessions.get_session(app_name="bloggeragent", user_id=user_id, session_id=session.id)
    return fake, events, session, artifacts


@pytest.fixture
def pipeline():
    return run_pipeline
