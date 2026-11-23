from datetime import date
from typing import Any
from uuid import UUID

from ninja import Schema

from ..models import MediaType, Release, ReviewStatus, Work
from .release import ReleaseOut, _can_edit
from .term import TermOut, TermRef


class WorkOut(Schema):
    id: UUID
    title: str
    media_type: MediaType
    summary: str
    # With ids: the edit form picks these (TermRef); names alone are on ReleaseOut.
    series: list[TermOut]
    franchises: list[TermOut]
    first_release_date: date | None
    genres: list[TermOut]
    developers: list[TermOut]
    cover_url: str | None  # its own cover, else the first release cover
    cover_aspect: float | None
    has_cover: bool  # a cover of its own (key art)
    # Ids at external sources ({"igdb": "1029"}): which game a source matched.
    external_ids: dict[str, str | int]
    releases: list[ReleaseOut]
    review_status: ReviewStatus
    can_edit: bool

    @staticmethod
    def resolve_can_edit(obj: Work, context: Any) -> bool:
        return _can_edit(obj, context)

    @staticmethod
    def resolve_cover_url(obj: Work) -> str | None:
        return obj.shown_cover()[0]

    @staticmethod
    def resolve_cover_aspect(obj: Work) -> float | None:
        return obj.shown_cover()[1]

    @staticmethod
    def resolve_has_cover(obj: Work) -> bool:
        return bool(obj.cover)

    @staticmethod
    def resolve_releases(obj: Work) -> list[Release]:
        return sorted(obj.releases.all(), key=lambda r: (r.sort_date, r.platform.name))


class WorkPatch(Schema):
    title: str | None = None
    summary: str | None = None
    series: list[TermRef] | None = None
    franchises: list[TermRef] | None = None
    first_release_date: date | None = None
    genres: list[TermRef] | None = None
    developers: list[TermRef] | None = None
