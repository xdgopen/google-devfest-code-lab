"""Early-exit for the validation loops.

In the original codelab the checkers answer "ok"/"retry" but nothing stops the
LoopAgent, so it always runs `max_iterations` times. `LoopGate` is a tiny,
deterministic (no LLM call) agent placed after each checker: it reads the
checker's verdict from state and escalates when it is "ok", which makes
`LoopAgent` exit immediately.
"""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent, InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types

_OK_RE = re.compile(r"^\W*ok\b", re.IGNORECASE)


def is_ok_verdict(verdict: object) -> bool:
    """True when a checker verdict means "passed" (e.g. "ok", "OK.", '"ok"')."""
    if not isinstance(verdict, str):
        return False
    text = verdict.strip()
    if not text or text.lower().startswith("retry"):
        return False
    return bool(_OK_RE.match(text))


class LoopGate(BaseAgent):
    """Escalates (exits the parent LoopAgent) when `state[verdict_key]` is ok."""

    verdict_key: str = "validation_result"
    counter_key: str = "loop_iterations"

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        verdict = state.get(self.verdict_key)
        passed = is_ok_verdict(verdict)

        counters = dict(state.get(self.counter_key) or {})
        loop_name = self.name.removesuffix("Gate")
        counters[loop_name] = int(counters.get(loop_name, 0)) + 1

        message = (
            f"{loop_name}: validation passed after {counters[loop_name]} iteration(s)."
            if passed
            else f"{loop_name}: validation requested a retry."
        )
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=message)]),
            actions=EventActions(
                escalate=passed,
                state_delta={self.counter_key: counters},
            ),
        )
