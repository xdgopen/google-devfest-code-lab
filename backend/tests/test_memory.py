"""Memory: profile memory (user: state) + long-term memory service."""

from google.adk.memory import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService

from bloggeragent import memory as m
from bloggeragent.config import Settings
from tests.fakes import FakeLlm


# ------------------------------ pure helpers ------------------------------- #
def test_merge_preferences_ignores_blank_and_unknown():
    merged = m.merge_preferences({"tone": "formal"}, {"tone": " ", "language": "vi", "x": "y"})
    assert merged == {"tone": "formal", "language": "vi"}


def test_apply_preferences_session_values_win():
    state = {"tone": "playful"}
    m.apply_preferences_to_session(state, {"tone": "formal", "audience": "SRE"})
    assert state == {"tone": "playful", "audience": "SRE"}


def test_build_history_entry_and_append_caps_size():
    entry = m.build_history_entry(
        {"blog_post": "# My Title\n\nbody", "blog_seo": {"slug": "my-title"},
         "blog_stats": {"word_count": 3}, "blog_topic": "topic"},
        "s1", today="2026-10-31",
    )
    assert entry == {"session_id": "s1", "topic": "topic", "title": "My Title",
                     "slug": "my-title", "words": 3, "date": "2026-10-31"}
    assert m.build_history_entry({}, "s1") is None
    history = []
    for i in range(m.MAX_HISTORY + 5):
        history = m.append_history(history, {**entry, "session_id": f"s{i}"})
    assert len(history) == m.MAX_HISTORY and history[-1]["session_id"] == f"s{m.MAX_HISTORY + 4}"
    # same session updated, not duplicated
    assert len(m.append_history([entry], {**entry, "title": "new"})) == 1


# ------------------------------ end-to-end --------------------------------- #
async def test_post_history_persists_across_sessions(pipeline):
    sessions, mem = InMemorySessionService(), InMemoryMemoryService()
    await pipeline(sessions=sessions, memory_service=mem)
    _, _, second, _ = await pipeline(sessions=sessions, memory_service=mem)
    history = second.state[m.HISTORY_KEY]
    assert len(history) == 2
    assert history[0]["title"] == "Planning Loops for AI Agents"
    assert history[0]["slug"] == "planning-loops-for-ai-agents"


async def test_history_is_isolated_per_user(pipeline):
    sessions, mem = InMemorySessionService(), InMemoryMemoryService()
    await pipeline(sessions=sessions, memory_service=mem, user_id="alice")
    _, _, bob, _ = await pipeline(sessions=sessions, memory_service=mem, user_id="bob")
    assert len(bob.state[m.HISTORY_KEY]) == 1


async def test_remembered_preferences_apply_to_next_session(pipeline):
    sessions, mem = InMemorySessionService(), InMemoryMemoryService()
    fake = FakeLlm(root_plan=[("remember_preferences", {"language": "Vietnamese", "tone": "friendly"})])
    await pipeline(sessions=sessions, memory_service=mem, fake=fake,
                   prompt="From now on always write in Vietnamese, friendly tone")
    fake2 = FakeLlm()
    _, _, second, _ = await pipeline(sessions=sessions, memory_service=mem, fake=fake2)
    assert second.state[m.PREFS_KEY] == {"language": "Vietnamese", "tone": "friendly"}
    assert "Output language: Vietnamese" in fake2.system_prompts["planner"]
    assert "Tone: friendly" in fake2.system_prompts["writer"]


async def test_sessions_are_added_to_long_term_memory(pipeline):
    sessions, mem = InMemorySessionService(), InMemoryMemoryService()
    await pipeline(sessions=sessions, memory_service=mem, prompt="Kubernetes operators deep dive")
    result = await mem.search_memory(app_name="bloggeragent", user_id="u1", query="Kubernetes")
    assert result.memories, "finished session should be searchable in memory"


async def test_recall_past_posts_tool(pipeline):
    sessions, mem = InMemorySessionService(), InMemoryMemoryService()
    await pipeline(sessions=sessions, memory_service=mem)
    fake = FakeLlm(root_plan=[("recall_past_posts", {"limit": 3})])
    _, events, _, _ = await pipeline(sessions=sessions, memory_service=mem, fake=fake)
    resp = next(p.function_response.response for e in events if e.content
                for p in e.content.parts if p.function_response)
    assert resp["count"] == 1 and resp["posts"][0]["slug"] == "planning-loops-for-ai-agents"


async def test_memory_can_be_disabled(pipeline):
    _, _, session, _ = await pipeline(settings=Settings(enable_memory=False))
    assert m.HISTORY_KEY not in session.state
