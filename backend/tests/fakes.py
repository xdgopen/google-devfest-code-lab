"""Offline fake Gemini model used to drive the whole agent tree in tests.

It identifies which agent is calling from the system instruction and replies
with scripted text / function calls, so the real ADK runtime (LoopAgent,
AgentTool, state, callbacks) is exercised without any network access.
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import AsyncGenerator

from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai import types
from pydantic import Field

OUTLINE = """# Planning Loops for AI Agents

Short intro about planning agents.

## Why planning
- reason
- act

## Loop agents
- retry
- validate

## Agent as tool
- wrap
- call

## State sharing
- output_key
- templates

## Conclusion
Wrap up.
"""

POST = """# Planning Loops for AI Agents

Agents that plan before acting produce better results.

## Why planning
Planning lets the model reason first.

```python
print("hello")
```

## Conclusion
Use LoopAgent with an early exit.
"""

FINAL = """Here is your post.

**Alternate titles**
1. Plan, Then Act
2. Loops That Self-Correct
3. Agents with a Checklist

**Hooks**
- Your agent should plan before it types.
- Self-correcting loops in 30 lines of Python.
"""


def _system_text(req: LlmRequest) -> str:
    si = req.config.system_instruction if req.config else None
    if si is None:
        return ""
    if isinstance(si, str):
        return si
    parts = getattr(si, "parts", None) or []
    return "".join(getattr(p, "text", "") or "" for p in parts)


def _function_responses(req: LlmRequest) -> list[str]:
    names = []
    for content in req.contents:
        for part in content.parts or []:
            if part.function_response:
                names.append(part.function_response.name)
    return names


ROLE_MARKERS = {
    "root": "If the user gives a topic",
    "planner": "technical content strategist",
    "outline_checker": "Check the outline",
    "writer": "Write a complete Markdown article",
    "post_checker": "Check `blog_post`",
    "researcher": "research assistant",
}


class FakeLlm(BaseLlm):
    """Scripted LLM. Configure verdict queues per checker before running."""

    model: str = "fake-gemini"
    verdicts: dict = {}
    root_plan: list = [
        ("RobustBlogPlanner", {"request": "topic"}),
        ("RobustBlogWriter", {"request": "write it"}),
        ("seo_suggestions", {"topic": "Planning loops for AI agents"}),
        ("text_stats", {}),
    ]

    calls: list = Field(default_factory=list)
    system_prompts: dict = Field(default_factory=dict)
    user_texts: list = Field(default_factory=list)
    overrides: dict = Field(default_factory=dict)  # role -> fixed reply text

    def model_post_init(self, __context) -> None:
        self._queues = defaultdict(deque)
        for role, items in (self.verdicts or {}).items():
            self._queues[role].extend(items)

    def _role(self, req: LlmRequest) -> str:
        text = _system_text(req)
        for role, marker in ROLE_MARKERS.items():
            if marker in text:
                return role
        return "unknown"

    def _reply(self, req: LlmRequest, role: str) -> types.Content:
        if role == "root":
            done = _function_responses(req)
            for name, args in self.root_plan:
                if name not in done:
                    return types.Content(
                        role="model",
                        parts=[types.Part(function_call=types.FunctionCall(name=name, args=args))],
                    )
            return types.Content(role="model", parts=[types.Part(text=FINAL)])
        if role in ("outline_checker", "post_checker"):
            queue = self._queues[role]
            verdict = queue.popleft() if queue else "ok"
            return types.Content(role="model", parts=[types.Part(text=verdict)])
        if role in self.overrides:
            return types.Content(role="model", parts=[types.Part(text=self.overrides[role])])
        text = {
            "planner": OUTLINE,
            "writer": POST,
            "researcher": "- Fact one (Source A)\n- Fact two (Source B)",
        }.get(role, "unknown agent")
        return types.Content(role="model", parts=[types.Part(text=text)])

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        role = self._role(llm_request)
        self.calls.append(role)
        self.system_prompts[role] = _system_text(llm_request)
        for content in llm_request.contents:
            if content.role == "user":
                self.user_texts.extend(p.text for p in content.parts or [] if p.text)
        yield LlmResponse(
            content=self._reply(llm_request, role),
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=10, candidates_token_count=5, total_token_count=15
            ),
        )
