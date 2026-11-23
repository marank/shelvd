"""Short descriptions of games for lists and pickers (title, platforms, a cover)."""

from __future__ import annotations

from typing import TypedDict
from uuid import UUID

from django.db.models import QuerySet

from ..models import Work


class WorkSummary(TypedDict):
    id: UUID
    title: str
    platforms: list[str]
    releases: int
    cover_url: str | None


def summaries(works: QuerySet[Work]) -> list[WorkSummary]:
    result: list[WorkSummary] = []
    for work in works.prefetch_related("releases__platform"):
        releases = list(work.releases.all())
        result.append(
            {
                "id": work.pk,
                "title": work.title,
                "platforms": sorted({r.platform.short_name or r.platform.name for r in releases}),
                "releases": len(releases),
                "cover_url": work.shown_cover()[0],
            }
        )
    return result
