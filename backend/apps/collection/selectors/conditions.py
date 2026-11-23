"""A view's filter conditions: field · operator · value, stored as short text.

    platform.name=<key>|<key>     is one of (group keys, as in the tree)
    platform.name!=<key>          is none of
    game.title~A*                 matches a pattern: * any text, ? one character, any
                                  case; without wildcards it means "contains"
    game.title!~*Demo*            doesn't match
    location.box?                 has a value (copies that are in a box)
    copy.notes!?                  is empty
    release.year>=2020            at least / at most (numbers, money, dates as YYYY-MM-DD)
    release.number><1..100        between, inclusive

Field keys are the same paths as everywhere (grouping, sorting, the frontend's field
registry). Like grouping, conditions are evaluated over the prefetched items.
"""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from django.utils.timezone import localdate
from django.utils.translation import gettext as _
from ninja.errors import HttpError

from ..models import Item
from .grouping import FIELDS, NONE_KEY, active_loan

# Grouping-only fields (first letter, decade) aren't filter fields of their own.
KEY_FIELDS = {k for k in FIELDS if k not in {"game.letter", "release.decade"}}


def _group_labels(field: str) -> Callable[[Item], list[str]]:
    def labels(item: Item) -> list[str]:
        return [v.label for v in FIELDS[field](item) if v.key != NONE_KEY]

    return labels


def _one(read: Callable[[Item], object | None]) -> Callable[[Item], list[str]]:
    def text(item: Item) -> list[str]:
        value = read(item)
        return [str(value)] if value not in (None, "") else []

    return text


TEXT: dict[str, Callable[[Item], list[str]]] = {
    **{field: _group_labels(field) for field in KEY_FIELDS},
    "game.title": _one(lambda i: i.display_title),
    "release.edition": _one(lambda i: i.shown.edition),
    "release.product_code": _one(lambda i: i.shown.product_code),
    "release.barcodes": lambda i: [b.code for b in i.shown.barcodes.all()],
    "release.number": _one(lambda i: i.shown.release_number),
    "copy.notes": _one(lambda i: i.notes),
}

Comparable = Decimal | date


# Cached facts of the game (catalog.WorkFact), as numbers.
FACT_FIELDS = {
    "game.time_main": ("hltb", "main"),
    "game.time_extra": ("hltb", "extra"),
    "game.time_complete": ("hltb", "complete"),
    "game.critic_score": ("opencritic", "score"),
    "game.critic_recommended": ("opencritic", "recommended"),
}


def fact_value(item: Item, source: str, name: str) -> Decimal | None:
    for fact in item.shown.work.facts.all():  # prefetched by the items selector
        if fact.source == source and isinstance(fact.values.get(name), (int, float)):
            return Decimal(str(fact.values[name]))
    return None


def _fact(source: str, name: str) -> Callable[[Item], Comparable | None]:
    return lambda item: fact_value(item, source, name)


def _loan_date(item: Item, name: str) -> date | None:
    loan = active_loan(item)
    value = getattr(loan, name) if loan else None
    return value if isinstance(value, date) else None


def _count(value: int | None) -> Decimal | None:
    return Decimal(value) if value is not None else None


NUMBERS: dict[str, Callable[[Item], Comparable | None]] = {
    "game.first_release": lambda i: i.shown.work.first_release_date,
    "release.year": lambda i: Decimal(i.shown.year) if i.shown.year else None,
    "release.number": lambda i: (
        Decimal(i.shown.release_number) if i.shown.release_number is not None else None
    ),
    "release.date": lambda i: i.shown.release_date and i.shown.sort_date,
    "release.players_offline": lambda i: _count(i.shown.players_offline),
    "release.players_online": lambda i: _count(i.shown.players_online),
    "platform.year": lambda i: (
        Decimal(i.shown.platform.release_year) if i.shown.platform.release_year else None
    ),
    "copy.value": lambda i: i.current_value,
    "copy.price": lambda i: i.purchase_price,
    "copy.acquired": lambda i: i.acquired_on,
    "copy.added": lambda i: localdate(i.created_at),
    **{key: _fact(source, name) for key, (source, name) in FACT_FIELDS.items()},
    "loan.since": lambda i: _loan_date(i, "lent_on"),
    "loan.due": lambda i: _loan_date(i, "due_on"),
}
DATE_FIELDS = {
    "game.first_release", "release.date", "copy.acquired", "copy.added", "loan.since", "loan.due",
}  # fmt: skip
KNOWN = set(TEXT) | set(NUMBERS)

PATTERN = re.compile(r"^([a-z_]+\.[a-z_]+)(!\?|\?|!~|~|!=|>=|<=|><|=)(.*)$", re.DOTALL)


@dataclass(frozen=True)
class Condition:
    field: str
    op: str
    values: tuple[str, ...] = ()
    low: Comparable | None = None
    high: Comparable | None = None


def _invalid() -> HttpError:
    return HttpError(400, _("Invalid filter."))


def _bound(field: str, raw: str) -> Comparable:
    try:
        return date.fromisoformat(raw) if field in DATE_FIELDS else Decimal(raw)
    except ValueError, InvalidOperation:
        raise _invalid() from None


def parse_condition(text: str, allowed: Iterable[str] | None = None) -> Condition | None:
    """One condition, or None when its field isn't allowed (public pages)."""
    match = PATTERN.match(text.strip())
    if not match:
        raise _invalid()
    field, op, value = match.groups()
    if field not in KNOWN:
        raise _invalid()
    if allowed is not None and field not in set(allowed):
        return None
    if op in {"=", "!="}:
        if field not in KEY_FIELDS or not value:
            raise _invalid()
        return Condition(field, op, tuple(value.split("|")))
    if op in {"~", "!~"}:
        return _text_condition(field, op, value)
    if op in {">=", "<=", "><"}:
        return _range_condition(field, op, value)
    if value:  # ? and !? take no value
        raise _invalid()
    return Condition(field, op)


def _text_condition(field: str, op: str, value: str) -> Condition:
    """Contains (~) or not (!~); with * or ? the value is a pattern for the whole text."""
    if field not in TEXT or not value:
        raise _invalid()
    pattern = value if any(c in value for c in "*?") else f"*{value}*"
    return Condition(field, op, (pattern.lower(),))


def _range_condition(field: str, op: str, value: str) -> Condition:
    """At least (>=), at most (<=) or between (><, `low..high`), both ends included."""
    if field not in NUMBERS:
        raise _invalid()
    if op == "><":
        low, sep, high = value.partition("..")
        if not sep:
            raise _invalid()
        return Condition(field, op, low=_bound(field, low), high=_bound(field, high))
    bound = _bound(field, value)
    return Condition(
        field, op, low=bound if op == ">=" else None, high=bound if op == "<=" else None
    )


def parse_conditions(texts: Iterable[str], allowed: Iterable[str] | None = None) -> list[Condition]:
    parsed = (parse_condition(text, allowed) for text in texts if text.strip())
    return [condition for condition in parsed if condition is not None]


def _holds(item: Item, c: Condition) -> bool:
    if c.op in {"=", "!="}:
        found = not {v.key for v in FIELDS[c.field](item)}.isdisjoint(c.values)
        return found if c.op == "=" else not found
    if c.op in {"~", "!~"}:
        found = any(fnmatch.fnmatchcase(t.lower(), c.values[0]) for t in TEXT[c.field](item))
        return found if c.op == "~" else not found
    if c.op in {">=", "<=", "><"}:
        value = NUMBERS[c.field](item)
        if value is None:
            return False
        return (c.low is None or value >= c.low) and (c.high is None or value <= c.high)  # type: ignore[operator]
    present = (
        NUMBERS[c.field](item) is not None if c.field in NUMBERS else bool(TEXT[c.field](item))
    )
    return present if c.op == "?" else not present


def satisfies(item: Item, conditions: list[Condition], any_of: bool = False) -> bool:
    if not conditions:
        return True
    results = (_holds(item, c) for c in conditions)
    return any(results) if any_of else all(results)
