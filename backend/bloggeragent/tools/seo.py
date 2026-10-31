"""Deterministic SEO helpers (no LLM call, fully unit-testable)."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

from google.adk.tools import ToolContext

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "for",
    "from", "how", "in", "into", "is", "it", "its", "of", "on", "or", "our",
    "that", "the", "their", "this", "to", "using", "use", "we", "what", "when",
    "why", "with", "you", "your", "vs", "between", "should", "guide",
}
META_MAX = 155


def slugify(text: str, max_length: int = 60) -> str:
    """ASCII, lowercase, dash-separated slug (handles Vietnamese accents)."""
    text = (text or "").replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    if len(slug) > max_length:
        slug = slug[:max_length].rsplit("-", 1)[0] or slug[:max_length]
    return slug


def extract_keywords(text: str, limit: int = 8) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}", (text or "").lower())
    words = [w.strip(".-") for w in words]
    counts = Counter(w for w in words if w and w not in STOPWORDS)
    return [w for w, _ in counts.most_common(limit)]


def _first_paragraph(markdown: str) -> str:
    for block in re.split(r"\n\s*\n", markdown or ""):
        block = block.strip()
        if block and not block.startswith(("#", "```", "-", "*", ">", "|")):
            return re.sub(r"[*_`\[\]]", "", " ".join(block.split()))
    return ""


def meta_description(topic: str, markdown: str = "") -> str:
    base = _first_paragraph(markdown) or f"A practical guide: {topic}".strip()
    if len(base) <= META_MAX:
        return base
    cut = base[: META_MAX - 1].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:") + "…"


def build_seo(topic: str, markdown: str = "") -> dict:
    keywords = extract_keywords(f"{topic} {topic} {markdown}")
    words = max(1, len(re.findall(r"\w+", markdown or "")))
    lower = (markdown or "").lower()
    density = {k: round(100 * lower.count(k) / words, 2) for k in keywords[:5]}
    return {
        "slug": slugify(topic),
        "meta_description": meta_description(topic, markdown),
        "keywords": keywords,
        "keyword_density_percent": density,
    }


def seo_suggestions(topic: str, tool_context: ToolContext) -> dict:
    """Suggests an SEO slug, meta description and keywords for the post.

    Args:
      topic: The blog topic or working title.

    Returns:
      A dict with slug, meta_description, keywords and keyword_density_percent.
    """
    seo = build_seo(topic, tool_context.state.get("blog_post", "") or "")
    tool_context.state["blog_seo"] = seo
    tool_context.state["blog_topic"] = topic
    return seo
