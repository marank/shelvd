"""Catalog terms – companies, genres, series: shared, pickable names."""

from typing import Any, Literal
from uuid import UUID

from ninja import Schema

from ..selectors.terms import description_for
from .catalog import PlatformOut

SUMMARY_LENGTH = 140


class TermRef(Schema):
    """A picked term: an existing one by `id`, or a new one by `name` (created on save;
    a name that exists already, in any case, is that term)."""

    id: UUID | None = None
    name: str = ""


class TermOut(Schema):
    id: UUID
    name: str


class TermSuggestionOut(Schema):
    """A term in suggestions and on its kind's overview page."""

    id: UUID
    name: str
    uses: int  # games (genres, series, developers) or releases (publishers) using it
    image_url: str | None
    image_tone: str  # how the picture reads: black/dark/white/light or "" (services.tones)
    summary: str  # the start of its description, in the reader's language if there
    country: str  # companies: ISO code, else ""
    founded: int | None  # companies only

    @staticmethod
    def resolve_image_url(obj: Any) -> str | None:
        return obj.image.url if obj.image else None

    @staticmethod
    def resolve_summary(obj: Any) -> str:
        text = description_for(obj.descriptions)[0].split("\n", 1)[0]
        return text if len(text) <= SUMMARY_LENGTH else text[: SUMMARY_LENGTH - 1].rstrip() + "…"

    @staticmethod
    def resolve_country(obj: Any) -> str:
        return str(getattr(obj, "country", ""))

    @staticmethod
    def resolve_founded(obj: Any) -> int | None:
        return getattr(obj, "founded", None)


class EditionOut(Schema):
    """An edition label in use and on how many releases (suggestions while typing)."""

    name: str
    uses: int


class TermWorkOut(Schema):
    """A game on a term's page."""

    id: UUID
    title: str
    year: int | None
    cover_url: str | None
    cover_aspect: float | None
    manufacturer: str  # tints the placeholder without a cover
    platforms: list[PlatformOut]


class RelatedTermOut(Schema):
    """Another term the same games have, and on how many of them."""

    kind: Literal["companies", "genres", "series", "franchises"]
    id: UUID
    name: str
    count: int


class PlatformGamesOut(Schema):
    """A platform's games and what they have in common."""

    works: list[TermWorkOut]
    related: list[RelatedTermOut]


class CompanyDetailsOut(Schema):
    """What is known about a company besides its games (empty strings / null: unknown)."""

    founded: int | None
    dissolved: int | None
    country: str  # ISO 3166-1 alpha-2, the UI names it
    headquarters: str
    website: str
    parent: TermOut | None
    subsidiaries: list[TermOut]


class CompanyDetailsIn(Schema):
    """All of a company's details at once (the edit page sends them together)."""

    founded: int | None = None
    dissolved: int | None = None
    country: str = ""
    headquarters: str = ""
    website: str = ""
    parent: TermRef | None = None  # an existing company, or a new one by name


class TermDetailOut(Schema):
    """A term's page: its games, oldest first (for a company: developed in `works`,
    published – a release of – in `published`) and what they have in common."""

    id: UUID
    name: str
    description: str  # in the reader's language, else another
    description_language: str  # which one ("" without any)
    descriptions: dict[str, str]  # every language's, for editing
    image_url: str | None
    image_tone: str  # how the picture reads: black/dark/white/light or "" (services.tones)
    works: list[TermWorkOut]
    published: list[TermWorkOut]
    related: list[RelatedTermOut]
    company: CompanyDetailsOut | None  # only for companies
    franchise: TermOut | None  # a series' franchise
    parts: list[TermOut]  # a franchise's series


class SeriesDetailsIn(Schema):
    """A series' franchise (an existing one, or none)."""

    franchise: TermRef | None = None


class TermPatch(Schema):
    name: str | None = None
    # Texts by language ("de", "en"); a language left out stays, an empty text removes it.
    descriptions: dict[str, str] | None = None
    company: CompanyDetailsIn | None = None  # companies only
    series: SeriesDetailsIn | None = None  # series only


class MergeTermIn(Schema):
    target_id: UUID
