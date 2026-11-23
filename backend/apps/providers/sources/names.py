"""Comparing the names of companies and series across sources."""

from __future__ import annotations

import re
import unicodedata

# "Square Enix Co., Ltd." → "Square Enix": legal forms at the end, one at a time.
LEGAL_FORM = re.compile(
    r"[\s,]+(?:inc|ltd|llc|co|corp|corporation|gmbh|ag|ab|hb|sas|sa|s\.a|plc|limited|kk|k\.k)\.?$",
    re.IGNORECASE,
)
# "Doom (2016)", "Metroid (Videospiel)" → the title without the disambiguation.
DISAMBIGUATION = re.compile(r"\s*\([^)]*\)$")


def strip_legal(name: str) -> str:
    while (stripped := LEGAL_FORM.sub("", name).strip()) != name:
        name = stripped
    return name


def normalize(name: str) -> str:
    """For comparing names: no disambiguation, legal form, case, accents ("Pokémon" is
    "Pokemon"), spaces or punctuation."""
    name = strip_legal(DISAMBIGUATION.sub("", name)).lower().replace("&", "and")
    name = "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c))
    return re.sub(r"[\W_]+", "", name)


# Words studios add or drop ("Bynine Studio" is "Bynine" at IGDB).
GENERIC_WORDS = re.compile(
    r"\s+(?:games|game|studios?|entertainment|interactive|software|productions?|digital)$",
    re.IGNORECASE,
)


def without_generic(name: str) -> str:
    """The name without a trailing generic word ("Studio", "Games" …); "" if that's all."""
    stripped = GENERIC_WORDS.sub("", strip_legal(name.strip()))
    return stripped if stripped.lower() != name.strip().lower() else ""


def variants(query: str) -> list[str]:
    """Other spellings to search when the name finds nothing fitting: without the legal
    form or trailing punctuation ("PlatinumGames Inc.", "Zoink!"), and run together
    ("Tiny Build" → "TinyBuild")."""
    base = strip_legal(query.strip()).strip(" !.,")
    found: list[str] = []
    for variant in (base, base.replace(" ", "")):
        if variant and variant.lower() != query.strip().lower() and variant not in found:
            found.append(variant)
    return found
