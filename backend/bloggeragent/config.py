"""Runtime configuration read from environment variables.

Kept dependency-free (plain dataclass) so it is trivial to unit test and
works identically under `adk web`, uvicorn and Cloud Run.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

_TRUE = {"1", "true", "yes", "on"}


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in _TRUE


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def _list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    model: str = "gemini-flash-latest"
    use_vertexai: bool = False
    google_cloud_project: str | None = None
    google_cloud_location: str | None = None
    enable_research: bool = False
    max_loop_iterations: int = 3
    max_input_chars: int = 2000
    database_url: str | None = None
    artifact_bucket: str | None = None
    enable_adk_web: bool = False
    allowed_origins: list[str] = field(default_factory=lambda: ["*"])
    log_level: str = "INFO"
    app_name: str = "bloggeragent"
    # memory
    enable_memory: bool = True
    memory_service_uri: str | None = None
    # guardrails
    max_tool_calls: int = 15
    blocked_topics: tuple[str, ...] = ()
    redact_pii: bool = True
    safety_threshold: str = "BLOCK_MEDIUM_AND_ABOVE"

    @property
    def auth_mode(self) -> str:
        """`vertex` on Cloud (ADC / service account) or `api_key` locally."""
        return "vertex" if self.use_vertexai else "api_key"

    @property
    def artifact_service_uri(self) -> str | None:
        return f"gs://{self.artifact_bucket}" if self.artifact_bucket else None

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            model=os.getenv("MODEL") or "gemini-flash-latest",
            use_vertexai=_bool("GOOGLE_GENAI_USE_VERTEXAI", False),
            google_cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT") or None,
            google_cloud_location=os.getenv("GOOGLE_CLOUD_LOCATION") or None,
            enable_research=_bool("ENABLE_RESEARCH", False),
            max_loop_iterations=max(1, _int("MAX_LOOP_ITERATIONS", 3)),
            max_input_chars=max(100, _int("MAX_INPUT_CHARS", 2000)),
            database_url=os.getenv("DATABASE_URL") or None,
            artifact_bucket=os.getenv("ARTIFACT_BUCKET") or None,
            enable_adk_web=_bool("ENABLE_ADK_WEB", False),
            allowed_origins=_list("ALLOWED_ORIGINS", ["*"]),
            log_level=(os.getenv("LOG_LEVEL") or "INFO").upper(),
            enable_memory=_bool("ENABLE_MEMORY", True),
            memory_service_uri=os.getenv("MEMORY_SERVICE_URI") or None,
            max_tool_calls=max(1, _int("MAX_TOOL_CALLS", 15)),
            blocked_topics=tuple(_list("BLOCKED_TOPICS", [])),
            redact_pii=_bool("REDACT_PII", True),
            safety_threshold=(os.getenv("SAFETY_THRESHOLD") or "BLOCK_MEDIUM_AND_ABOVE").upper(),
        )
