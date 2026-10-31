"""Blogger multi-agent system (Google ADK codelab, extended).

Structure (agent names identical to the codelab):

  Blogger (root)
  ├── tool: RobustBlogPlanner  (LoopAgent)
  │         BlogPlanner → OutlineValidationChecker → OutlineGate (early exit)
  ├── tool: RobustBlogWriter   (LoopAgent)
  │         BlogWriter  → BlogPostValidationChecker → BlogPostGate (early exit)
  ├── tool: Researcher          (google_search, optional: ENABLE_RESEARCH)
  ├── tools: fetch_repo_context, seo_suggestions, text_stats
  └── memory: preload_memory, remember_preferences, recall_past_posts

Guardrails (see guardrails.py): input checks, PII/secret redaction both ways,
tool budget + argument allow-list, Gemini safety settings.
"""

from __future__ import annotations

import datetime

from dotenv import load_dotenv
from google.adk.agents import Agent, LoopAgent
from google.adk.tools import agent_tool, google_search, preload_memory
from google.genai import types

from . import guardrails, memory, prompts
from .callbacks import make_usage_logger, save_post_artifact
from .config import Settings
from .tools import LoopGate, fetch_repo_context, seo_suggestions, text_stats

# env config
load_dotenv()


def build_root_agent(settings: Settings | None = None, model=None) -> Agent:
    """Builds the whole agent tree.

    `model` may be a model id string or a `BaseLlm` instance (tests inject a
    fake LLM here so the full pipeline runs offline).
    """
    settings = settings or Settings.from_env()
    model = model or settings.model
    # Guardrail layers 2, 4, 5 + usage logging apply to every LLM agent.
    common = {
        "model": model,
        "before_model_callback": guardrails.make_request_redactor(settings.redact_pii),
        "after_model_callback": [guardrails.output_redactor, make_usage_logger(settings)],
        "generate_content_config": types.GenerateContentConfig(
            safety_settings=guardrails.safety_settings(settings.safety_threshold)
        ),
    }

    # Sub-Agent: Planner
    blog_planner = Agent(
        name="BlogPlanner",
        description="Creates a practical, skimmable outline in Markdown.",
        instruction=prompts.PLANNER_INSTRUCTION,
        output_key="blog_outline",
        **common,
    )
    outline_checker = Agent(
        name="OutlineValidationChecker",
        description="Validates that the outline is usable.",
        instruction=prompts.OUTLINE_CHECKER_INSTRUCTION,
        output_key="validation_result",
        **common,
    )
    robust_blog_planner = LoopAgent(
        name="RobustBlogPlanner",
        description="Retries planning if validation fails.",
        sub_agents=[blog_planner, outline_checker, LoopGate(name="RobustBlogPlannerGate")],
        max_iterations=settings.max_loop_iterations,
    )

    # Sub-Agent: Writer
    blog_writer = Agent(
        name="BlogWriter",
        description="Writes a technical blog post from the outline.",
        instruction=prompts.WRITER_INSTRUCTION,
        output_key="blog_post",
        **common,
    )
    post_checker = Agent(
        name="BlogPostValidationChecker",
        description="Validates the final post.",
        instruction=prompts.POST_CHECKER_INSTRUCTION,
        output_key="validation_result",
        **common,
    )
    robust_blog_writer = LoopAgent(
        name="RobustBlogWriter",
        description="Retries writing if validation fails.",
        sub_agents=[blog_writer, post_checker, LoopGate(name="RobustBlogWriterGate")],
        max_iterations=settings.max_loop_iterations,
    )

    # Expose planner/writer as tools so the root agent can call them explicitly
    tools = [
        agent_tool.AgentTool(agent=robust_blog_planner),
        agent_tool.AgentTool(agent=robust_blog_writer),
        fetch_repo_context,
        seo_suggestions,
        text_stats,
    ]
    if settings.enable_memory:
        tools += [preload_memory, memory.remember_preferences, memory.recall_past_posts]
    if settings.enable_research:
        # Built-in google_search must live alone in its agent → wrap as a tool.
        researcher = Agent(
            name="Researcher",
            description="Researches facts about a topic with Google Search.",
            instruction=prompts.RESEARCH_INSTRUCTION,
            tools=[google_search],
            output_key="research_notes",
            **common,
        )
        tools.insert(0, agent_tool.AgentTool(agent=researcher))

    root_instruction = prompts.ROOT_INSTRUCTION_TEMPLATE.format(
        research_step=(
            prompts.RESEARCH_STEP_ON if settings.enable_research else prompts.RESEARCH_STEP_OFF
        ),
        date=datetime.datetime.now().strftime("%Y-%m-%d"),
    )

    # Root Agent: Plan → Write
    return Agent(
        name="Blogger",
        description="Minimal multi-agent blogger that plans and writes.",
        instruction=root_instruction,
        tools=tools,
        before_agent_callback=[
            guardrails.make_input_guardrail(
                settings.max_input_chars,
                guardrails.DEFAULT_BLOCKED_TOPICS + settings.blocked_topics,
            ),
            *([memory.load_profile_memory] if settings.enable_memory else []),
        ],
        before_tool_callback=guardrails.make_tool_guardrail(settings.max_tool_calls),
        after_agent_callback=[
            save_post_artifact,
            *([memory.save_memories] if settings.enable_memory else []),
        ],
        **common,
    )


root_agent = build_root_agent()
