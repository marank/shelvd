from datetime import date
from typing import Any
from uuid import UUID

from ninja import Schema

from apps.accounts.models import User

from ..models import DatePrecision, Region, Release, ReviewStatus
from ..selectors.review import can_edit
from .catalog import CompanyOut, PlatformOut
from .fact import FactOut
from .term import TermOut, TermRef


def _can_edit(obj: Any, context: Any) -> bool:
    """For the person asking: may they change this catalog entry?"""
    request = (context or {}).get("request")
    user = getattr(request, "user", None)
    return isinstance(user, User) and can_edit(user, obj)


class ReleaseOut(Schema):
    id: UUID
    title: str
    work_id: UUID
    work_title: str
    platform: PlatformOut
    region: Region
    edition: str
    age_rating: str
    product_code: str
    release_number: int | None
    series: list[TermOut]
    franchises: list[TermOut]
    first_release_date: date | None  # of the game, for the game's detail block
    release_date: date | None
    release_date_end: date | None
    release_precision: DatePrecision
    sort_date: date
    is_released: bool
    year: int | None
    publisher: CompanyOut | None
    developers: list[TermOut]  # the game's
    release_developers: list[TermOut]  # this release's own, besides the game's
    genres: list[TermOut]
    summary: str
    # How it's played (the game's, in IGDB's English names) and how many on this platform.
    game_modes: list[str]
    perspectives: list[str]
    languages: dict[str, list[str]]
    players_offline: int | None
    players_online: int | None
    cover_url: str | None  # its own cover, else the game's
    cover_aspect: float | None  # width / height; None without cover
    cover_source: str
    cover_from_game: bool  # no cover of its own: cover_url is the game's
    barcodes: list[str]
    pending_barcodes: list[str]  # assigned by someone, not reviewed yet
    review_status: ReviewStatus
    can_edit: bool  # may the person asking change it (admins; creators while unreviewed)
    # The game's cached facts by source (play time, critic score …).
    facts: dict[str, FactOut]

    @staticmethod
    def resolve_title(obj: Release) -> str:
        return obj.display_title

    @staticmethod
    def resolve_facts(obj: Release) -> dict[str, FactOut]:
        return {
            f.source: FactOut.model_validate(f, from_attributes=True) for f in obj.work.facts.all()
        }

    @staticmethod
    def resolve_first_release_date(obj: Release) -> date | None:
        return obj.work.first_release_date

    @staticmethod
    def resolve_work_title(obj: Release) -> str:
        return obj.work.title

    @staticmethod
    def resolve_developers(obj: Release) -> list[Any]:
        return list(obj.work.developers.all())

    @staticmethod
    def resolve_release_developers(obj: Release) -> list[Any]:
        return list(obj.developers.all())

    @staticmethod
    def resolve_genres(obj: Release) -> list[Any]:
        return list(obj.work.genres.all())

    @staticmethod
    def resolve_series(obj: Release) -> list[Any]:
        return list(obj.work.series.all())

    @staticmethod
    def resolve_franchises(obj: Release) -> list[Any]:
        return list(obj.work.franchises.all())

    @staticmethod
    def resolve_summary(obj: Release) -> str:
        return obj.work.summary

    @staticmethod
    def resolve_game_modes(obj: Release) -> list[str]:
        return list(obj.work.game_modes)

    @staticmethod
    def resolve_perspectives(obj: Release) -> list[str]:
        return list(obj.work.perspectives)

    @staticmethod
    def resolve_languages(obj: Release) -> dict[str, list[str]]:
        return dict(obj.work.languages)

    @staticmethod
    def resolve_cover_from_game(obj: Release) -> bool:
        return not obj.cover and bool(obj.work.cover)

    @staticmethod
    def resolve_barcodes(obj: Release) -> list[str]:
        return [b.code for b in obj.barcodes.all()]

    @staticmethod
    def resolve_pending_barcodes(obj: Release) -> list[str]:
        return [b.code for b in obj.barcodes.all() if b.pending]

    @staticmethod
    def resolve_can_edit(obj: Release, context: Any) -> bool:
        return _can_edit(obj, context)


class ReleaseIn(Schema):
    """Manual entry when no provider knows the game. work_id adds a release to an
    existing work (e.g. the same game on another platform)."""

    title: str
    platform_id: UUID
    region: Region = Region.PAL
    work_id: UUID | None = None
    edition: str = ""
    age_rating: str = ""
    product_code: str = ""
    release_number: int | None = None
    series: list[TermRef] = []
    franchises: list[TermRef] = []
    release_date: date | None = None
    release_date_end: date | None = None
    release_precision: DatePrecision = DatePrecision.DAY
    publisher: TermRef | None = None
    developers: list[TermRef] = []
    genres: list[TermRef] = []
    summary: str = ""
    barcode: str | None = None


class ReleasePatch(Schema):
    """Fields of one release. The game itself (genres, developers, summary) is WorkPatch."""

    title: str | None = None
    platform_id: UUID | None = None
    region: Region | None = None
    edition: str | None = None
    age_rating: str | None = None
    product_code: str | None = None
    release_number: int | None = None
    release_date: date | None = None
    release_date_end: date | None = None
    release_precision: DatePrecision | None = None
    # A picked company; null removes the publisher.
    publisher: TermRef | None = None
    # Studios that worked on this release only (the game's developers are WorkPatch).
    release_developers: list[TermRef] | None = None


class BarcodeIn(Schema):
    code: str
