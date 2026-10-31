"""Agent callbacks: structured usage logging and artifact export.

Guardrail callbacks live in `guardrails.py`, memory callbacks in `memory.py`.
"""

from __future__ import annotations

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.genai import types

from .config import Settings
from .logging_utils import get_logger, log_event

ARTIFACT_MD = "blog_post.md"


def make_usage_logger(settings: Settings):
    """after_model_callback: log one JSON line per model call with token usage."""
    logger = get_logger(settings.log_level)

    def log_model_usage(
        callback_context: CallbackContext, llm_response: LlmResponse
    ) -> LlmResponse | None:
        usage = llm_response.usage_metadata
        log_event(
            logger,
            "model_call",
            agent=callback_context.agent_name,
            invocation_id=callback_context.invocation_id,
            model=settings.model,
            prompt_tokens=getattr(usage, "prompt_token_count", None),
            output_tokens=getattr(usage, "candidates_token_count", None),
            total_tokens=getattr(usage, "total_token_count", None),
        )
        return None

    return log_model_usage


async def save_post_artifact(callback_context: CallbackContext) -> None:
    """after_agent_callback (root): persist the final post as an artifact.

    Uses whatever artifact service the runner was built with: GCS on Cloud Run
    (ARTIFACT_BUCKET), local/in-memory otherwise. Failures never break a chat.
    """
    post = callback_context.state.get("blog_post")
    if not post:
        return None
    try:
        version = await callback_context.save_artifact(
            ARTIFACT_MD,
            types.Part.from_bytes(data=post.encode("utf-8"), mime_type="text/markdown"),
        )
        callback_context.state["blog_artifact_version"] = version
    except Exception as exc:  # artifact service not configured / unavailable
        log_event(get_logger(), "artifact_save_failed", error=str(exc))
    return None
