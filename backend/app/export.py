"""Markdown → safe standalone HTML export."""

from __future__ import annotations

import html

import markdown as md

HTML_TEMPLATE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<style>
body{{font-family:Nunito,system-ui,sans-serif;max-width:760px;margin:40px auto;padding:0 16px;color:#3c3c3c;line-height:1.6}}
pre{{background:#f4f4f4;padding:12px;border-radius:12px;overflow:auto}}
code{{font-family:ui-monospace,Menlo,monospace}}
a{{color:#0a6fa3}}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def markdown_to_safe_html(text: str) -> str:
    """Render Markdown while dropping raw HTML blocks/inline HTML (XSS-safe)."""
    renderer = md.Markdown(extensions=["fenced_code", "tables"])
    renderer.preprocessors.deregister("html_block")
    renderer.inlinePatterns.deregister("html")
    return renderer.convert(text or "")


def to_html_document(post: str, title: str = "", description: str = "", lang: str = "en") -> str:
    return HTML_TEMPLATE.format(
        lang=html.escape(lang or "en"),
        title=html.escape(title or "Blog post"),
        description=html.escape(description or ""),
        body=markdown_to_safe_html(post),
    )
