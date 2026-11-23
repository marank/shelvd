"""Editions written into titles ("Dave the Diver: Complete Edition") belong on the release.

split_edition() is used by importers; the catalog stays "one game, several releases".
"""

from __future__ import annotations

import re

# Known edition endings, optionally after ":", "-", "–" or in brackets.
EDITION_SUFFIX = re.compile(
    r"\s*[-:–(]?\s*(?P<edition>"
    r"(?:nintendo\s+)?switch\s+2\s+edition"
    r"|(?:complete|definitive|deluxe|ultimate|gold|royal|enhanced|special|collector'?s"
    r"|game\s+of\s+the\s+year|goty|launch|day\s+one|digital\s+deluxe|premium|legendary"
    r"|(?:\d+(?:st|nd|rd|th)\s+)?anniversary)\s+edition"
    r"|director'?s\s+cut)\)?\s*$",
    re.IGNORECASE,
)


def split_edition(title: str) -> tuple[str, str]:
    """("Dave The Diver: Complete Edition") → ("Dave The Diver", "Complete Edition")."""
    match = EDITION_SUFFIX.search(title)
    if not match or match.start() == 0:
        return title.strip(), ""
    base = title[: match.start()].strip(" -:–")
    return (base, match.group("edition").strip()) if base else (title.strip(), "")
