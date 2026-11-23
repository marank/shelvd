"""Sorting a library's items by any field, over several levels
("location.box,-release.number").

Keys are the same as the frontend's field registry (`lib/itemFields.ts`), so a view can
sort by anything it could show, shown or not. Grouping fields reuse the order of their
groups (`grouping.FIELDS`); the rest are read here. Empty values always come last.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from django.utils.translation import gettext as _
from ninja.errors import HttpError

from ..models import Item
from .conditions import FACT_FIELDS, fact_value
from .grouping import FIELDS, NONE_KEY, active_loan, sort_title

SortKey = Callable[[Item], object | None]

MAX_LEVELS = 5


def _group(field: str) -> SortKey:
    """Order of the item's first group of that field (None: no value)."""

    def key(item: Item) -> object | None:
        first = FIELDS[field](item)[0]
        return None if first.key == NONE_KEY else first.sort

    return key


def _fact(source: str, name: str) -> SortKey:
    return lambda item: fact_value(item, source, name)


def _text(value: str | None) -> str | None:
    return value.strip().lower() or None if value else None


# Grouping-only fields (first letter, decade) aren't sort keys of their own.
SORT_KEYS: dict[str, SortKey] = {
    **{field: _group(field) for field in FIELDS if field not in {"game.letter", "release.decade"}},
    "game.title": lambda i: sort_title(i.display_title),
    "game.first_release": lambda i: i.shown.work.first_release_date,
    "release.edition": lambda i: _text(i.shown.edition),
    "release.date": lambda i: i.shown.sort_date,
    "release.number": lambda i: i.shown.release_number,
    "release.product_code": lambda i: _text(i.shown.product_code),
    "release.barcodes": lambda i: min((b.code for b in i.shown.barcodes.all()), default=None),
    "copy.value": lambda i: i.current_value,
    "copy.price": lambda i: i.purchase_price,
    "copy.acquired": lambda i: i.acquired_on,
    "copy.added": lambda i: i.created_at,
    "copy.notes": lambda i: _text(i.notes),
    "loan.to": lambda i: (loan := active_loan(i)) and loan.borrower.name.lower(),
    **{key: _fact(source, name) for key, (source, name) in FACT_FIELDS.items()},
    "loan.since": lambda i: (loan := active_loan(i)) and loan.lent_on,
    "loan.due": lambda i: (loan := active_loan(i)) and loan.due_on,
}


def parse_sort(spec: str, allowed: Iterable[str] | None = None) -> list[tuple[str, bool]]:
    """ "location.box,-release.number" → [("location.box", False), ("release.number", True)].
    Keys outside
    `allowed` (public pages) are dropped; unknown keys are an error."""
    levels: list[tuple[str, bool]] = []
    permitted = set(allowed) if allowed is not None else None
    for part in (p.strip() for p in spec.split(",")):
        if not part:
            continue
        desc = part.startswith("-")
        key = part.lstrip("-")
        if key not in SORT_KEYS:
            raise HttpError(400, _("Unknown sort order."))
        if permitted is None or key in permitted:
            levels.append((key, desc))
    if len(levels) > MAX_LEVELS:
        raise HttpError(400, _("Unknown sort order."))
    return levels


def sort_items(items: list[Item], levels: list[tuple[str, bool]]) -> list[Item]:
    """Stable passes from the last level to the first, titles as the final tie-break."""
    result = sorted(items, key=lambda item: sort_title(item.display_title))
    for key, desc in reversed(levels):
        values = [(item, SORT_KEYS[key](item)) for item in result]
        filled = [pair for pair in values if pair[1] is not None]
        filled.sort(key=lambda pair: pair[1], reverse=desc)  # type: ignore[arg-type,return-value]
        result = [item for item, _value in filled] + [
            item for item, value in values if value is None
        ]
    return result
