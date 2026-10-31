"""Layered guardrails for the Blogger agent.

Layer 1 – input   (before_agent_callback on root): empty/too-long input,
                   prompt-injection heuristics, blocked topics, secret leakage.
Layer 2 – model   (before_model_callback, all LLM agents): redact PII
                   (emails, phone numbers) before text leaves for Gemini.
Layer 3 – tools   (before_tool_callback on root): per-invocation tool-call
                   budget, argument validation (GitHub host allow-list).
Layer 4 – output  (after_model_callback, all LLM agents): redact secrets/PII
                   that the model might echo back.
Layer 5 – Gemini safety settings (generate_content_config).

All checks are pure functions first (unit-testable), wrapped as ADK callbacks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.tools import BaseTool, ToolContext
from google.genai import types

from .logging_utils import get_logger, log_event

# --------------------------------------------------------------------------- #
# Patterns
# --------------------------------------------------------------------------- #
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above)\s+(instructions|prompts?|rules)",
    r"disregard\s+(all\s+|the\s+)?(previous|prior|above|system)",
    r"(reveal|print|show|repeat|leak)\s+(me\s+)?(your|the)\s+(system\s+)?(prompt|instructions)",
    r"you\s+are\s+now\s+(?:in\s+)?(dan|developer\s+mode|jailbreak)",
    r"bỏ\s+qua\s+(tất\s+cả\s+)?(các\s+)?(hướng\s+dẫn|chỉ\s+dẫn)\s+(trước|ở\s+trên)",
]
_INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)

DEFAULT_BLOCKED_TOPICS = (
    "build a bomb", "make explosives", "write malware", "ransomware",
    "credit card dump", "child sexual", "synthesize nerve agent",
)

SECRET_PATTERNS = {
    "google_api_key": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "openai_like_key": re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"),
}
PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"(?<![\w.])(?:\+?84|0)(?:[\s.-]?\d){9,10}(?!\w)|\+\d{1,3}[\s.-]?\(?\d{2,4}\)?(?:[\s.-]?\d{3,4}){2}"),
}

ALLOWED_REPO_HOSTS = ("github.com", "www.github.com")


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    reason: str = ""
    code: str = ""


# --------------------------------------------------------------------------- #
# Pure checks
# --------------------------------------------------------------------------- #
def check_input(
    text: str, max_chars: int, blocked_topics: tuple[str, ...] = DEFAULT_BLOCKED_TOPICS
) -> GuardrailResult:
    text = (text or "").strip()
    if not text:
        return GuardrailResult(False, "Please enter a blog topic.", "empty")
    if len(text) > max_chars:
        return GuardrailResult(
            False,
            f"Your request is {len(text)} characters long; the limit is {max_chars}. "
            "Please shorten the topic description.",
            "too_long",
        )
    if _INJECTION_RE.search(text):
        return GuardrailResult(
            False,
            "This request looks like an attempt to override the assistant's "
            "instructions, so it was not processed. Please describe a blog topic.",
            "prompt_injection",
        )
    lower = text.lower()
    for topic in blocked_topics:
        if topic and topic.lower() in lower:
            return GuardrailResult(
                False, "This topic is not allowed by the content policy.", "blocked_topic"
            )
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            return GuardrailResult(
                False,
                "Your message seems to contain a secret (e.g. an API key). It was "
                "not sent to the model – please remove it and try again.",
                f"secret:{name}",
            )
    return GuardrailResult(True)


def redact(text: str, include_pii: bool = True) -> tuple[str, list[str]]:
    """Masks secrets (always) and PII (optional). Returns (text, found_kinds)."""
    found: list[str] = []
    patterns = dict(SECRET_PATTERNS)
    if include_pii:
        patterns.update(PII_PATTERNS)
    for name, pattern in patterns.items():
        if pattern.search(text or ""):
            found.append(name)
            text = pattern.sub(f"[REDACTED_{name.upper()}]", text)
    return text, found


def check_tool_call(
    tool_name: str, args: dict[str, Any], calls_so_far: int, max_calls: int
) -> GuardrailResult:
    if calls_so_far >= max_calls:
        return GuardrailResult(
            False, f"Tool budget exceeded ({max_calls} calls per request).", "tool_budget"
        )
    if tool_name == "fetch_repo_context":
        url = str(args.get("github_url", "")).strip().lower()
        host = re.sub(r"^https?://", "", url).split("/", 1)[0]
        if host not in ALLOWED_REPO_HOSTS:
            return GuardrailResult(
                False, "Only public github.com repository URLs are allowed.", "host_not_allowed"
            )
    if tool_name == "seo_suggestions" and len(str(args.get("topic", ""))) > 300:
        return GuardrailResult(False, "Topic argument too long.", "arg_too_long")
    return GuardrailResult(True)


def safety_settings(threshold: str = "BLOCK_MEDIUM_AND_ABOVE") -> list[types.SafetySetting]:
    categories = [
        types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    ]
    return [
        types.SafetySetting(category=c, threshold=types.HarmBlockThreshold(threshold))
        for c in categories
    ]


# --------------------------------------------------------------------------- #
# ADK callback factories
# --------------------------------------------------------------------------- #
def _user_text(content: types.Content | None) -> str:
    if not content or not content.parts:
        return ""
    return "".join(p.text or "" for p in content.parts)


def make_input_guardrail(max_chars: int, blocked_topics: tuple[str, ...] = DEFAULT_BLOCKED_TOPICS):
    """before_agent_callback (root): stop the run with a polite message."""
    logger = get_logger()

    def input_guardrail(callback_context: CallbackContext) -> types.Content | None:
        result = check_input(_user_text(callback_context.user_content), max_chars, blocked_topics)
        if result.allowed:
            callback_context.state["guardrail_blocked"] = False
            return None
        callback_context.state["guardrail_blocked"] = True
        callback_context.state["guardrail_reason"] = result.code
        log_event(logger, "guardrail_blocked", layer="input", code=result.code)
        return types.Content(role="model", parts=[types.Part(text=result.reason)])

    return input_guardrail


def make_request_redactor(redact_pii: bool = True):
    """before_model_callback: mask PII/secrets in user text sent to the model."""

    def redact_request(callback_context: CallbackContext, llm_request: LlmRequest) -> None:
        hits: list[str] = []
        for content in llm_request.contents or []:
            if content.role != "user":
                continue
            for part in content.parts or []:
                if part.text:
                    part.text, found = redact(part.text, include_pii=redact_pii)
                    hits.extend(found)
        if hits:
            callback_context.state["temp:redacted_input"] = sorted(set(hits))
        return None

    return redact_request


def make_tool_guardrail(max_calls: int):
    """before_tool_callback (root): budget + argument validation."""
    logger = get_logger()

    def tool_guardrail(
        tool: BaseTool, args: dict[str, Any], tool_context: ToolContext
    ) -> dict | None:
        key = f"temp:tool_calls_{tool_context.invocation_id}"
        calls = int(tool_context.state.get(key, 0) or 0)
        result = check_tool_call(tool.name, args, calls, max_calls)
        if not result.allowed:
            log_event(logger, "guardrail_blocked", layer="tool", tool=tool.name, code=result.code)
            return {"status": "error", "error": result.reason}
        tool_context.state[key] = calls + 1
        return None

    return tool_guardrail


def output_redactor(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> LlmResponse | None:
    """after_model_callback: never let secrets (or PII) leave in model output."""
    content = llm_response.content
    if not content or not content.parts:
        return None
    changed = False
    for part in content.parts:
        if part.text:
            new_text, found = redact(part.text, include_pii=True)
            if found:
                part.text = new_text
                changed = True
    return llm_response if changed else None
