from datetime import date
from uuid import UUID

from ninja import Schema

from apps.catalog.models import Region
from apps.catalog.schemas import ReleaseOut


class CandidateOut(Schema):
    """A provider's suggestion; nothing is stored until it is imported."""

    provider: str
    external_id: str
    title: str
    platform_id: UUID | None
    platform_name: str
    region: str | None
    release_date: date | None
    release_precision: str
    year: int | None
    publisher: str
    developers: list[str]
    genres: list[str]
    summary: str
    cover_url: str


class SearchOut(Schema):
    query: str
    platform_id: UUID | None
    candidates: list[CandidateOut]
    errors: list[str]


class BarcodeLookupOut(Schema):
    code: str
    # Releases this barcode is already confirmed for (usually exactly one).
    known: list[ReleaseOut]


class ImportIn(Schema):
    provider: str
    external_id: str
    platform_id: UUID
    region: Region
    barcode: str | None = None


class ProviderOut(Schema):
    name: str
    label: str
    kind: str  # metadata | facts | covers | playtime
    enabled: bool
