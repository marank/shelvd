"""Reading items: full-text-ish search across all fields, filters, sorting."""

from __future__ import annotations

from django.db.models import Q, QuerySet

from apps.providers.services import gtin

from ..models import Item, Library
from .conditions import Condition, satisfies
from .grouping import matches
from .sorting import parse_sort, sort_items


def base_queryset(library: Library) -> QuerySet[Item]:
    return (
        Item.objects.filter(library=library)
        .select_related(
            "release__work",
            "release__platform",
            "release__publisher",
            "location__parent__parent__parent",
            "owner",
        )
        .prefetch_related(
            "release__work__genres",
            "release__work__developers",
            "release__developers",
            "release__work__series",
            "release__work__franchises",
            "release__work__facts",
            "release__barcodes",
            "loans__borrower",
            "tags",
        )
    )


def search_q(query: str) -> Q:
    """Every word must match at least one field (title, platform, company, genre,
    barcode, location, people, notes, …)."""
    condition = Q()
    for word in query.split():
        fields = Q()
        for lookup in (
            "title_override",
            "release__work__title",
            "release__title",
            "release__edition",
            "release__product_code",
            "release__age_rating",
            "release__work__series__name",
            "release__work__franchises__name",
            "tags__name",
            "release__platform__name",
            "release__platform__short_name",
            "release__platform__manufacturer",
            "release__publisher__name",
            "release__work__developers__name",
            "release__developers__name",
            "release__work__genres__name",
            "release__region",
            "location__name",
            "location__parent__name",
            "owner__name",
            "loans__borrower__name",
            "notes",
        ):
            fields |= Q(**{f"{lookup}__icontains": word})
        code = gtin.normalize(word)
        if code:
            fields |= Q(release__barcodes__code=code)
        condition &= fields
    return condition


def list_items(
    library: Library,
    *,
    query: str = "",
    filters: dict[str, list[str]] | None = None,
    sort: str = "game.title",
    sortable: set[str] | None = None,
    conditions: list[Condition] | None = None,
    any_of: bool = False,
) -> list[Item]:
    queryset = base_queryset(library)
    if query.strip():
        ids = Item.objects.filter(library=library).filter(search_q(query)).values("pk")
        queryset = queryset.filter(pk__in=ids)
    items = [
        item
        for item in queryset
        if matches(item, filters or {}) and satisfies(item, conditions or [], any_of)
    ]
    return sort_items(items, parse_sort(sort, sortable))
