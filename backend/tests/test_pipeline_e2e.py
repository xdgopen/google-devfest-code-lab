"""End-to-end run of the real ADK runtime with a fake model (offline)."""

from bloggeragent.config import Settings
from tests.fakes import FINAL, OUTLINE, POST


async def test_full_pipeline_produces_outline_post_and_final(pipeline):
    fake, events, session, _ = await pipeline()
    state = session.state
    assert state["blog_outline"].strip() == OUTLINE.strip()
    assert state["blog_post"].strip() == POST.strip()
    final_texts = [p.text for e in events if e.content for p in e.content.parts if p.text]
    assert final_texts[-1].strip() == FINAL.strip()


async def test_loops_exit_early_when_checkers_say_ok(pipeline):
    fake, _, session, _ = await pipeline()
    assert fake.calls.count("planner") == 1
    assert fake.calls.count("writer") == 1
    assert session.state["loop_iterations"] == {"RobustBlogPlanner": 1, "RobustBlogWriter": 1}


async def test_retry_then_ok_runs_extra_iterations(pipeline):
    fake, _, session, _ = await pipeline(
        verdicts={"outline_checker": ["retry: missing conclusion", "ok"],
                  "post_checker": ["retry: add code", "retry: still", "ok"]}
    )
    assert fake.calls.count("planner") == 2
    assert fake.calls.count("writer") == 3
    assert session.state["loop_iterations"]["RobustBlogPlanner"] == 2


async def test_loop_stops_at_max_iterations(pipeline):
    fake, _, _, _ = await pipeline(
        verdicts={"outline_checker": ["retry"] * 10},
        settings=Settings(max_loop_iterations=3),
    )
    assert fake.calls.count("planner") == 3


async def test_seo_and_stats_written_to_state(pipeline):
    _, _, session, _ = await pipeline()
    assert session.state["blog_seo"]["slug"] == "planning-loops-for-ai-agents"
    assert session.state["blog_stats"]["code_block_count"] == 1


async def test_post_saved_as_artifact(pipeline):
    _, _, session, artifacts = await pipeline()
    part = await artifacts.load_artifact(
        app_name="bloggeragent", user_id="u1", session_id=session.id, filename="blog_post.md"
    )
    assert part.inline_data.data.decode().strip() == POST.strip()


async def test_preferences_are_injected_into_prompts(pipeline):
    fake, _, _, _ = await pipeline(
        initial_state={"tone": "friendly", "audience": "beginners", "language": "Vietnamese"}
    )
    assert "Tone: friendly" in fake.system_prompts["planner"]
    assert "Output language: Vietnamese" in fake.system_prompts["writer"]


async def test_guardrail_blocks_long_input_without_model_call(pipeline):
    fake, events, session, _ = await pipeline(
        prompt="x" * 500, settings=Settings(max_input_chars=100)
    )
    assert fake.calls == []
    assert session.state.get("guardrail_blocked") is True
    assert "limit is 100" in events[-1].content.parts[0].text
