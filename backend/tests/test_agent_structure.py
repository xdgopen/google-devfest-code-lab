"""The agent tree keeps the codelab's names/contract and adds the extensions."""

from google.adk.agents import LoopAgent
from google.adk.tools.agent_tool import AgentTool

from bloggeragent.agent import build_root_agent, root_agent
from bloggeragent.config import Settings
from bloggeragent.tools import LoopGate


def _tool_names(agent):
    return [getattr(t, "name", None) or t.__name__ for t in agent.tools]


def test_module_level_root_agent_for_adk_cli():
    assert root_agent.name == "Blogger"


def test_codelab_structure_is_preserved():
    agent = build_root_agent(Settings())
    tools = {t.agent.name: t.agent for t in agent.tools if isinstance(t, AgentTool)}
    planner, writer = tools["RobustBlogPlanner"], tools["RobustBlogWriter"]
    assert isinstance(planner, LoopAgent) and isinstance(writer, LoopAgent)
    assert planner.max_iterations == 3 and writer.max_iterations == 3
    assert [a.name for a in planner.sub_agents] == [
        "BlogPlanner", "OutlineValidationChecker", "RobustBlogPlannerGate"]
    assert [a.name for a in writer.sub_agents] == [
        "BlogWriter", "BlogPostValidationChecker", "RobustBlogWriterGate"]
    assert planner.sub_agents[0].output_key == "blog_outline"
    assert writer.sub_agents[0].output_key == "blog_post"
    assert planner.sub_agents[1].output_key == "validation_result"
    assert isinstance(planner.sub_agents[2], LoopGate)


def test_extension_tools_present():
    names = _tool_names(build_root_agent(Settings()))
    for expected in ["fetch_repo_context", "seo_suggestions", "text_stats",
                     "preload_memory", "remember_preferences", "recall_past_posts"]:
        assert expected in names
    assert "Researcher" not in names


def test_research_and_memory_toggles():
    names = _tool_names(build_root_agent(Settings(enable_research=True, enable_memory=False)))
    assert names[0] == "Researcher"
    assert "preload_memory" not in names


def test_max_iterations_configurable_and_model_override():
    agent = build_root_agent(Settings(max_loop_iterations=5, model="gemini-3.5-flash"))
    loops = [t.agent for t in agent.tools if isinstance(t, AgentTool) and isinstance(t.agent, LoopAgent)]
    assert all(loop.max_iterations == 5 for loop in loops)
    assert agent.model == "gemini-3.5-flash"


def test_safety_settings_applied_to_every_llm_agent():
    agent = build_root_agent(Settings())
    assert len(agent.generate_content_config.safety_settings) == 4
    planner = next(t.agent for t in agent.tools if getattr(t, "name", "") == "RobustBlogPlanner")
    assert planner.sub_agents[0].generate_content_config.safety_settings
