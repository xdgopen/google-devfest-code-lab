"""Unit tests for the pure tool logic."""

import httpx
import pytest
import respx

from bloggeragent.tools import compute_text_stats, is_ok_verdict
from bloggeragent.tools.repo_context import load_repo_context, parse_github_url
from bloggeragent.tools.seo import build_seo, extract_keywords, meta_description, slugify


# ------------------------------ loop control ------------------------------- #
@pytest.mark.parametrize("v", ["ok", "OK", " ok.", '"ok"', "Ok - looks good"])
def test_ok_verdicts(v):
    assert is_ok_verdict(v)


@pytest.mark.parametrize("v", ["retry", "Retry: ok-ish but missing", "", None, 1, "okay?", "not ok"])
def test_non_ok_verdicts(v):
    assert not is_ok_verdict(v)


# ------------------------------ text stats --------------------------------- #
def test_text_stats_counts_and_ignores_code():
    md = "# Title\n\nHello world again.\n\n## Part\n\n```py\nignored words here\n```\n"
    stats = compute_text_stats(md)
    assert stats["word_count"] == 5  # Title, Hello, world, again, Part
    assert stats["code_block_count"] == 1
    assert stats["h2_count"] == 1 and stats["heading_count"] == 2
    assert stats["reading_time_minutes"] == 1


def test_text_stats_empty_and_long():
    assert compute_text_stats("")["reading_time_minutes"] == 0
    assert compute_text_stats("word " * 1100)["reading_time_minutes"] == 5


# ------------------------------ seo ---------------------------------------- #
def test_slugify_handles_vietnamese_and_length():
    assert slugify("Xây dựng AI Agent với Google ADK!") == "xay-dung-ai-agent-voi-google-adk"
    assert slugify("Đường đi") == "duong-di"
    assert len(slugify("word " * 40)) <= 60
    assert not slugify("x" * 80).endswith("-")


def test_keywords_skip_stopwords():
    kws = extract_keywords("The Docker and the Docker compose for Postgres with Docker")
    assert kws[0] == "docker"
    assert "the" not in kws and "with" not in kws


def test_meta_description_from_first_paragraph_and_truncates():
    md = "# T\n\n" + "Long sentence about agents " * 20
    meta = meta_description("topic", md)
    assert len(meta) <= 155 and meta.endswith("…")
    assert meta_description("REST vs gRPC") == "A practical guide: REST vs gRPC"


def test_build_seo_shape():
    seo = build_seo("Python asyncio", "# Asyncio\n\nPython asyncio makes concurrency easy.")
    assert seo["slug"] == "python-asyncio"
    assert "asyncio" in seo["keywords"]
    assert seo["keyword_density_percent"]["asyncio"] > 0


# ------------------------------ repo context ------------------------------- #
@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://github.com/google/adk-python", ("google", "adk-python")),
        ("github.com/google/adk-python.git", ("google", "adk-python")),
        ("https://github.com/a/b/tree/main/src", ("a", "b")),
        ("https://gitlab.com/a/b", None),
        ("not a url", None),
    ],
)
def test_parse_github_url(url, expected):
    assert parse_github_url(url) == expected


@respx.mock
async def test_load_repo_context_success_and_truncation():
    respx.get("https://api.github.com/repos/google/adk-python").mock(
        return_value=httpx.Response(200, json={"description": "ADK", "language": "Python",
                                               "topics": ["agents"]})
    )
    respx.get("https://api.github.com/repos/google/adk-python/readme").mock(
        return_value=httpx.Response(200, text="R" * 10000)
    )
    result = await load_repo_context("https://github.com/google/adk-python")
    assert result["status"] == "success" and result["truncated"] is True
    assert result["context"].startswith("Repository: google/adk-python")
    assert "Topics: agents" in result["context"]


@respx.mock
async def test_load_repo_context_errors():
    respx.get("https://api.github.com/repos/x/missing").mock(return_value=httpx.Response(404))
    assert (await load_repo_context("https://github.com/x/missing"))["error"] == "GitHub returned 404"
    respx.get("https://api.github.com/repos/x/down").mock(side_effect=httpx.ConnectError("boom"))
    assert "Network error" in (await load_repo_context("https://github.com/x/down"))["error"]
    assert (await load_repo_context("https://example.com"))["status"] == "error"


@respx.mock
async def test_fetch_repo_context_tool_sets_state(pipeline):
    from tests.fakes import FakeLlm
    respx.get("https://api.github.com/repos/google/adk-python").mock(
        return_value=httpx.Response(200, json={"description": "ADK"}))
    respx.get("https://api.github.com/repos/google/adk-python/readme").mock(
        return_value=httpx.Response(200, text="# ADK readme"))
    fake = FakeLlm(root_plan=[
        ("fetch_repo_context", {"github_url": "https://github.com/google/adk-python"}),
        ("RobustBlogPlanner", {"request": "plan"}),
    ])
    _, _, session, _ = await pipeline(fake=fake)
    assert "# ADK readme" in session.state["codebase_context"]
    assert "# ADK readme" in fake.system_prompts["planner"]  # injected into planner
