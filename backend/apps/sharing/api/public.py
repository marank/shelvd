"""Read-only views behind an unguessable token; no account needed."""

from decimal import Decimal

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import P, Query, QueryEx, Router

from apps.collection.api.items import node_out
from apps.collection.models import Item, Library
from apps.collection.schemas import PublicItemOut, TreeOut
from apps.collection.selectors.filters import check_fields, parse_filters
from apps.collection.selectors.grouping import Node, build_tree
from apps.collection.selectors.items import list_items
from apps.core.api.errors import ErrorOut
from apps.core.api.pagination import Page

from ..models import CustomList
from ..schemas import PublicLibraryOut, PublicListOut
from .lists import entries

router = Router(tags=["public"], auth=None)
ERRORS = {400: ErrorOut, 404: ErrorOut}

# Groupings that would reveal private data (people, places) are not offered publicly.
PUBLIC_FIELDS = {
    "game.series", "game.franchises", "game.genres", "game.developers", "game.kind", "game.letter",
    "game.modes", "game.perspectives", "game.languages",
    "release.year", "release.decade", "release.region", "release.age_rating", "release.developers",
    "release.players_offline", "release.players_online",
    "platform.name", "platform.manufacturer", "platform.year", "publisher.name",
    "copy.format", "copy.status", "copy.completeness",
}  # fmt: skip
# Sorting may use catalog fields, never people, places, prices or notes.
PUBLIC_SORTS = PUBLIC_FIELDS | {
    "game.title", "game.first_release", "release.edition", "release.date", "release.number",
    "release.product_code", "game.time_main", "game.time_extra", "game.time_complete",
    "game.critic_score", "game.critic_recommended",
}  # fmt: skip


def _without_values(nodes: list[Node]) -> list[Node]:
    """Copies' values are private; zero them on every level of a public tree."""
    for node in nodes:
        node.value = Decimal(0)
        _without_values(node.children)
    return nodes


def _library(token: str) -> Library:
    return get_object_or_404(Library.objects.select_related("owner"), public_token=token)


def _public_fields(keys: list[str]) -> list[str]:
    return check_fields([key for key in keys if key in PUBLIC_FIELDS])


@router.get("libraries/{token}", response={200: PublicLibraryOut, **ERRORS})
def public_library(request: HttpRequest, token: str) -> PublicLibraryOut:
    library = _library(token)
    return PublicLibraryOut(
        name=library.name,
        description=library.description,
        owner=library.owner.get_username(),
        item_count=library.items.count(),
    )


@router.get("libraries/{token}/tree", response={200: TreeOut, **ERRORS})
def public_tree(
    request: HttpRequest,
    token: str,
    group_by: Query[list[str] | None] = None,
    filters: QueryEx[list[str] | None, P(alias="filter")] = None,
) -> TreeOut:
    library = _library(token)
    allowed = {k: v for k, v in parse_filters(filters or []).items() if k in PUBLIC_FIELDS}
    found = list_items(library, filters=allowed)
    fields = _public_fields(group_by or [])
    nodes = build_tree(found, fields)
    # Values are private: the public tree reports none.
    return TreeOut(
        total=len(found),
        total_value=Decimal(0),
        group_by=fields,
        nodes=[node_out(n) for n in _without_values(nodes)],
    )


@router.get("libraries/{token}/items", response={200: Page[PublicItemOut], **ERRORS})
def public_items(
    request: HttpRequest,
    token: str,
    filters: QueryEx[list[str] | None, P(alias="filter")] = None,
    sort: str = "game.title",
    limit: int = 100,
    offset: int = 0,
) -> Page[Item]:
    library = _library(token)
    allowed = {k: v for k, v in parse_filters(filters or []).items() if k in PUBLIC_FIELDS}
    found = list_items(library, filters=allowed, sort=sort, sortable=PUBLIC_SORTS)
    limit = max(1, min(limit, 500))
    return Page(count=len(found), items=found[offset : offset + limit])


@router.get("lists/{token}", response={200: PublicListOut, **ERRORS})
def public_list(request: HttpRequest, token: str) -> PublicListOut:
    custom_list = get_object_or_404(CustomList.objects.select_related("owner"), public_token=token)
    return PublicListOut(
        name=custom_list.name,
        description=custom_list.description,
        owner=custom_list.owner.get_username(),
        entries=list(entries(custom_list)),  # type: ignore[arg-type]
    )
