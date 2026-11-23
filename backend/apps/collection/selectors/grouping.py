"""Free nesting of a library: any sequence of fields (platform › publisher › year …).

Every field knows how to read its group value(s) from an item. Items with several
values (genres, developers) appear in several groups. Grouping runs in Python over the
prefetched items — fine for personal collections of a few thousand items, and it keeps
tree, filter and item list consistent with each other.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import date
from decimal import Decimal

from django.utils.timezone import localdate

from ..models import Item, Loan
from ..models.choices import LocationKind

NONE_KEY = "none"

# Leading articles don't count when sorting titles ("The Witcher 3" sorts under W).
ARTICLES = re.compile(r"^(the|a|an|der|die|das|ein|eine|le|la|les|el|los|las)\s+", re.IGNORECASE)


def sort_title(title: str) -> str:
    return ARTICLES.sub("", title.strip()).lower()


@dataclass(frozen=True)
class GroupValue:
    key: str
    label: str
    sort: tuple[object, ...] = ()


Extractor = Callable[[Item], list[GroupValue]]


def _one(key: object | None, label: str | None, *sort: object) -> list[GroupValue]:
    if key in (None, ""):
        return [GroupValue(NONE_KEY, "", (1,))]
    return [GroupValue(str(key), label or str(key), (0, *sort, (label or "").lower()))]


def _platform(item: Item) -> list[GroupValue]:
    p = item.shown.platform
    # Platforms without a manufacturer (PC …) after the console makers.
    return _one(p.pk, p.name, p.manufacturer.lower() or "~", p.release_year or 0)


def _year(item: Item) -> list[GroupValue]:
    year = item.shown.year
    return _one(year, str(year) if year else None, year or 0)


def _decade(item: Item) -> list[GroupValue]:
    year = item.shown.year
    decade = year // 10 * 10 if year else None
    return _one(decade, f"{decade}s" if decade else None, decade or 0)


def _location(item: Item) -> list[GroupValue]:
    loc = item.location
    return _one(loc.pk, loc.path, loc.path.lower()) if loc else _one(None, None)


def _location_root(item: Item) -> list[GroupValue]:
    loc = item.location
    while loc is not None and loc.parent is not None:
        loc = loc.parent
    return _one(loc.pk, loc.name) if loc else _one(None, None)


# Order of place kinds from outside in, for sorting by a place's kind.
KIND_ORDER = {"room": 0, "furniture": 1, "shelf": 2, "box": 3, "other": 4}


def _location_kind(item: Item) -> list[GroupValue]:
    loc = item.location
    return _one(loc.kind, loc.kind, KIND_ORDER.get(loc.kind, 9)) if loc else _one(None, None)


def _location_name(item: Item) -> list[GroupValue]:
    loc = item.location
    return _one(loc.name.lower(), loc.name) if loc else _one(None, None)


def _platform_year(item: Item) -> list[GroupValue]:
    year = item.shown.platform.release_year
    return _one(year, str(year) if year else None, year or 0)


def _loan_overdue(item: Item) -> list[GroupValue]:
    loan = active_loan(item)
    overdue = loan is not None and loan.due_on is not None and loan.due_on < localdate()
    return _one("yes" if overdue else None, "yes")


def _location_of_kind(kind: str) -> Extractor:
    """The nearest place of this kind the copy is in (itself or a parent): its box,
    its shelf … so a nesting can say "platform › box" whatever room the box is in."""

    def extract(item: Item) -> list[GroupValue]:
        loc = item.location
        seen: set[object] = set()
        while loc is not None and loc.pk not in seen:
            if loc.kind == kind:
                return _one(loc.pk, loc.name, loc.name.lower(), loc.path.lower())
            seen.add(loc.pk)
            loc = loc.parent
        return _one(None, None)

    return extract


def _month(day: date | None) -> list[GroupValue]:
    """A month as "2026-03"; the newest first."""
    if day is None:
        return _one(None, None)
    key = f"{day.year:04d}-{day.month:02d}"
    return _one(key, key, -(day.year * 12 + day.month))


def _loan(item: Item) -> list[GroupValue]:
    loan = active_loan(item)
    return _one(loan.borrower_id, loan.borrower.name) if loan else _one(None, None)


def _letter(item: Item) -> list[GroupValue]:
    first = (sort_title(item.display_title)[:1] or "#").upper()
    letter = first if first.isalpha() else "#"
    return _one(letter, letter)


def _many(values: Iterable[tuple[object, str]]) -> list[GroupValue]:
    groups = [GroupValue(str(key), label, (0, label.lower())) for key, label in values]
    return groups or _one(None, None)


def _players(count: int | None) -> list[GroupValue]:
    return _one(count, str(count) if count else None, count)


def _choice(attr: str) -> Extractor:
    def extract(item: Item) -> list[GroupValue]:
        value = getattr(item, attr)
        return _one(value, value)

    return extract


# Keys are paths: the object (game, release, platform, publisher, copy, location, owner,
# loan) and its field. The frontend's field registry uses the same keys.
FIELDS: dict[str, Extractor] = {
    "game.series": lambda i: _many((s.pk, s.name) for s in i.shown.work.series.all()),
    "game.franchises": lambda i: _many((f.pk, f.name) for f in i.shown.work.franchises.all()),
    "game.genres": lambda i: _many((g.pk, g.name) for g in i.shown.work.genres.all()),
    "game.developers": lambda i: _many((c.pk, c.name) for c in i.shown.work.developers.all()),
    # How it's played, in IGDB's English names (the frontend translates them).
    "game.modes": lambda i: _many((m, m) for m in i.shown.work.game_modes),
    "game.perspectives": lambda i: _many((p, p) for p in i.shown.work.perspectives),
    "game.languages": lambda i: _many((name, name) for name in i.shown.work.languages),
    "game.kind": lambda i: _one(i.shown.platform.media_type, i.shown.platform.media_type),
    "game.letter": _letter,
    "release.year": _year,
    "release.decade": _decade,
    "release.region": lambda i: _one(i.shown.region, i.shown.region),
    "release.age_rating": lambda i: _one(i.shown.age_rating, i.shown.age_rating),
    "release.players_offline": lambda i: _players(i.shown.players_offline),
    "release.players_online": lambda i: _players(i.shown.players_online),
    "release.developers": lambda i: _many((c.pk, c.name) for c in i.shown.developers.all()),
    "platform.name": _platform,
    "platform.manufacturer": lambda i: _one(
        i.shown.platform.manufacturer, i.shown.platform.manufacturer
    ),
    "platform.year": _platform_year,
    "publisher.name": lambda i: _one(
        i.shown.publisher_id, i.shown.publisher.name if i.shown.publisher else None
    ),
    "copy.status": _choice("status"),
    "copy.format": _choice("format"),
    "copy.condition": _choice("condition"),
    "copy.completeness": _choice("completeness"),
    "copy.progress": _choice("play_status"),
    "copy.tags": lambda i: _many((t.pk, t.name) for t in i.tags.all()),
    "copy.added": lambda i: _month(localdate(i.created_at)),
    "copy.acquired": lambda i: _month(i.acquired_on),
    "location.path": _location,
    "location.name": _location_name,
    "location.kind": _location_kind,
    "location.room": _location_root,
    "location.shelf": _location_of_kind(LocationKind.SHELF),
    "location.box": _location_of_kind(LocationKind.BOX),
    "owner.name": lambda i: _one(i.owner_id, i.owner.name if i.owner else None),
    "loan.to": _loan,
    "loan.overdue": _loan_overdue,
}


def active_loan(item: Item) -> Loan | None:
    # Prefetched by the items selector; avoids one query per item.
    loans = [loan for loan in item.loans.all() if loan.returned_on is None]
    return loans[0] if loans else None


@dataclass
class Node:
    field: str
    key: str
    label: str
    count: int = 0
    value: Decimal = Decimal(0)
    children: list[Node] = dataclass_field(default_factory=list)
    _index: dict[str, Node] = dataclass_field(default_factory=dict, repr=False)
    _sort: tuple[object, ...] = ()


def build_tree(items: Iterable[Item], group_by: list[str]) -> list[Node]:
    root = Node(field="", key="", label="")
    for item in items:
        _insert(root, item, group_by)
    return _finish(root.children)


def _insert(node: Node, item: Item, group_by: list[str]) -> None:
    if not group_by:
        return
    field_key, rest = group_by[0], group_by[1:]
    for value in FIELDS[field_key](item):
        child = node._index.get(value.key)
        if child is None:
            child = Node(field=field_key, key=value.key, label=value.label, _sort=value.sort)
            node._index[value.key] = child
            node.children.append(child)
        child.count += 1
        child.value += item.current_value or 0
        _insert(child, item, rest)


def _finish(nodes: list[Node]) -> list[Node]:
    nodes.sort(key=lambda n: n._sort)
    for node in nodes:
        node.children = _finish(node.children)
    return nodes


@dataclass
class Section:
    """A run of the item list under one heading; `start` is its first row."""

    field: str
    key: str
    label: str
    count: int
    value: Decimal
    start: int


def split_sections(items: Iterable[Item], field_key: str) -> tuple[list[Item], list[Section]]:
    """The items in the order of the field's groups, keeping their order within a group.
    An item with several values (genres) is listed under each of them."""
    buckets: dict[str, tuple[GroupValue, list[Item]]] = {}
    for item in items:
        for value in FIELDS[field_key](item):
            buckets.setdefault(value.key, (value, []))[1].append(item)
    rows: list[Item] = []
    sections: list[Section] = []
    for value, members in sorted(buckets.values(), key=lambda b: b[0].sort):
        sections.append(
            Section(
                field=field_key,
                key=value.key,
                label=value.label,
                count=len(members),
                value=sum((i.current_value or Decimal(0) for i in members), Decimal(0)),
                start=len(rows),
            )
        )
        rows.extend(members)
    return rows, sections


def matches(item: Item, filters: dict[str, list[str]]) -> bool:
    """All fields must match; within a field any of the given keys."""
    for field_key, keys in filters.items():
        if not keys:
            continue
        values = {v.key for v in FIELDS[field_key](item)}
        if values.isdisjoint(keys):
            return False
    return True
