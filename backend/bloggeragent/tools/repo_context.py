"""Fetch a public GitHub repository README into state `codebase_context`.

The original codelab prompt says "If `codebase_context` exists in state…" but
never sets it; this tool closes that gap.
"""

from __future__ import annotations

import re

import httpx
from google.adk.tools import ToolContext

MAX_CONTEXT_CHARS = 6000
_REPO_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?(?:/.*)?$"
)
GITHUB_API = "https://api.github.com"


def parse_github_url(url: str) -> tuple[str, str] | None:
    match = _REPO_RE.match((url or "").strip())
    if not match:
        return None
    return match.group(1), match.group(2)


async def load_repo_context(url: str, client: httpx.AsyncClient | None = None) -> dict:
    parsed = parse_github_url(url)
    if not parsed:
        return {"status": "error", "error": f"Not a GitHub repository URL: {url}"}
    owner, repo = parsed
    headers = {"Accept": "application/vnd.github.raw+json", "User-Agent": "bloggeragent"}
    own_client = client is None
    client = client or httpx.AsyncClient(timeout=10)
    try:
        meta = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}")
        if meta.status_code != 200:
            return {"status": "error", "error": f"GitHub returned {meta.status_code}"}
        info = meta.json()
        readme = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/readme", headers=headers
        )
        readme_text = readme.text if readme.status_code == 200 else ""
    except httpx.HTTPError as exc:
        return {"status": "error", "error": f"Network error: {exc}"}
    finally:
        if own_client:
            await client.aclose()

    context = (
        f"Repository: {owner}/{repo}\n"
        f"Description: {info.get('description') or '-'}\n"
        f"Primary language: {info.get('language') or '-'}\n"
        f"Topics: {', '.join(info.get('topics') or []) or '-'}\n\n"
        f"README:\n{readme_text}"
    )
    truncated = len(context) > MAX_CONTEXT_CHARS
    return {
        "status": "success",
        "repo": f"{owner}/{repo}",
        "truncated": truncated,
        "context": context[:MAX_CONTEXT_CHARS],
    }


async def fetch_repo_context(github_url: str, tool_context: ToolContext) -> dict:
    """Loads a public GitHub repository's description and README as context.

    Args:
      github_url: URL like https://github.com/google/adk-python

    Returns:
      status, repo and whether the context was truncated. The context itself is
      stored in state `codebase_context` for the planner.
    """
    result = await load_repo_context(github_url)
    if result["status"] == "success":
        tool_context.state["codebase_context"] = result["context"]
        return {k: v for k, v in result.items() if k != "context"}
    return result
