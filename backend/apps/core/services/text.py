"""Plain text from the bits of HTML other tools put into descriptions."""

from __future__ import annotations

import html
import re

_BREAKS = [
    (re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE), "\n"),
    (re.compile(r"<\s*/?\s*p\b[^>]*>", re.IGNORECASE), "\n\n"),
    (re.compile(r"<\s*li\b[^>]*>", re.IGNORECASE), "\n• "),
    (re.compile(r"<\s*/?\s*(?:ul|ol)\b[^>]*>", re.IGNORECASE), "\n\n"),
]
_TAG = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")


def plain_text(text: str) -> str:
    """Line breaks, paragraphs and list items kept (as "• …" lines), every other tag
    dropped, entities decoded, blank lines collapsed."""
    if "<" not in text and "&" not in text:
        return text.strip()
    for pattern, replacement in _BREAKS:
        text = pattern.sub(replacement, text)
    text = html.unescape(_TAG.sub("", text))
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    # List items stay together.
    return re.sub(r"(^• .*)\n\n(?=• )", r"\1\n", text, flags=re.MULTILINE).strip()
