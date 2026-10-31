"""Builds the ADK runtime services from Settings.

| Service  | Local / tests          | Google Cloud                          |
|----------|------------------------|---------------------------------------|
| Session  | InMemory or Postgres   | DatabaseSessionService → Cloud SQL    |
| Artifact | InMemory               | GcsArtifactService (ARTIFACT_BUCKET)  |
| Memory   | InMemory               | Vertex AI Memory Bank (agentengine://)|
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from google.adk.agents import BaseAgent
from google.adk.artifacts import BaseArtifactService, InMemoryArtifactService
from google.adk.memory import BaseMemoryService, InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, InMemorySessionService

from bloggeragent.config import Settings

BACKEND_DIR = Path(__file__).resolve().parents[1]


def normalize_db_url(url: str) -> str:
    """Use async drivers: postgres → psycopg (v3), sqlite → aiosqlite."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("sqlite:///"):
        return "sqlite+aiosqlite:///" + url[len("sqlite:///"):]
    return url


def build_session_service(settings: Settings) -> BaseSessionService:
    if settings.database_url:
        from google.adk.sessions import DatabaseSessionService

        return DatabaseSessionService(db_url=normalize_db_url(settings.database_url))
    return InMemorySessionService()


def build_artifact_service(settings: Settings) -> BaseArtifactService:
    if settings.artifact_bucket:
        from google.adk.artifacts import GcsArtifactService

        return GcsArtifactService(bucket_name=settings.artifact_bucket)
    return InMemoryArtifactService()


def build_memory_service(settings: Settings) -> BaseMemoryService:
    if settings.memory_service_uri:
        from google.adk.cli.utils.service_factory import create_memory_service_from_options

        return create_memory_service_from_options(
            base_dir=BACKEND_DIR, memory_service_uri=settings.memory_service_uri
        )
    return InMemoryMemoryService()


@dataclass
class AppServices:
    settings: Settings
    agent: BaseAgent
    sessions: BaseSessionService
    artifacts: BaseArtifactService
    memory: BaseMemoryService
    runner: Runner

    @property
    def app_name(self) -> str:
        return self.settings.app_name


def build_services(
    settings: Settings,
    agent: BaseAgent | None = None,
    sessions: BaseSessionService | None = None,
    artifacts: BaseArtifactService | None = None,
    memory: BaseMemoryService | None = None,
) -> AppServices:
    if agent is None:
        from bloggeragent.agent import build_root_agent

        agent = build_root_agent(settings)
    sessions = sessions or build_session_service(settings)
    artifacts = artifacts or build_artifact_service(settings)
    memory = memory or build_memory_service(settings)
    runner = Runner(
        app_name=settings.app_name,
        agent=agent,
        session_service=sessions,
        artifact_service=artifacts,
        memory_service=memory,
    )
    return AppServices(settings, agent, sessions, artifacts, memory, runner)
