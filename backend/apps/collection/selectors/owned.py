"""Which games a library has: lets catalog pages (companies, genres, series) and the add
dialog mark them without the catalog knowing about libraries."""

from __future__ import annotations

from typing import TypedDict
from uuid import UUID

from django.db.models import Count

from ..models import Item, ItemStatus, Library


class OwnedRelease(TypedDict):
    release_id: UUID
    work_id: UUID
    copies: int


def owned_releases(library: Library) -> list[OwnedRelease]:
    """Every release with at least one owned (not sold) copy, its game and how many."""
    rows = (
        Item.objects.filter(library=library, status=ItemStatus.OWNED)
        .values("release_id", "release__work_id")
        .annotate(copies=Count("id"))
        .order_by("release_id")
    )
    return [
        {
            "release_id": row["release_id"],
            "work_id": row["release__work_id"],
            "copies": row["copies"],
        }
        for row in rows
    ]
