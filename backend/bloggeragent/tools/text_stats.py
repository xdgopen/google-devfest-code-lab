"""Pure text statistics for a Markdown blog post + an ADK tool wrapper."""

from __future__ import annotations

import re

from google.adk.tools import ToolContext

WORDS_PER_MINUTE = 220
_WORD_RE = re.compile(r"[\w'’-]+", re.UNICODE)
_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$", re.MULTILINE)


def compute_text_stats(markdown: str) -> dict:
    """Word count, reading time, headings and code-block count of Markdown."""
    markdown = markdown or ""
    code_blocks = _CODE_FENCE_RE.findall(markdown)
    prose = _CODE_FENCE_RE.sub(" ", markdown)
    words = _WORD_RE.findall(prose)
    headings = [
        {"level": len(m.group(1)), "text": m.group(2)}
        for m in _HEADING_RE.finditer(prose)
    ]
    word_count = len(words)
    minutes = max(1, round(word_count / WORDS_PER_MINUTE)) if word_count else 0
    return {
        "word_count": word_count,
        "reading_time_minutes": minutes,
        "heading_count": len(headings),
        "h2_count": sum(1 for h in headings if h["level"] == 2),
        "code_block_count": len(code_blocks),
        "headings": headings,
    }


def text_stats(tool_context: ToolContext, text: str = "") -> dict:
    """Computes word count, reading time and structure of the blog post.

    Args:
      text: Markdown to analyse. Leave empty to analyse the current draft
        stored in state `blog_post`.

    Returns:
      A dict with word_count, reading_time_minutes, heading_count, h2_count,
      code_block_count and headings.
    """
    source = text or tool_context.state.get("blog_post", "") or ""
    stats = compute_text_stats(source)
    tool_context.state["blog_stats"] = stats
    return stats
