from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from ninja import Schema

from apps.catalog.models import DatePrecision, Region
from apps.catalog.schemas import ReleaseOut

from ..models import (
    Completeness,
    Condition,
    Item,
    ItemFormat,
    ItemStatus,
    PlayStatus,
    ViewerLoans,
)
from ..selectors.grouping import active_loan
from .loan import LoanRef
from .location import LocationRef
from .person import PersonRef


class ItemOut(Schema):
    id: UUID
    library_id: UUID
    # Effective title and cover: the library's override, else the catalog's.
    title: str
    cover_url: str | None
    cover_aspect: float | None
    title_override: str
    has_cover_override: bool
    edition_override: str
    region_override: Region | None
    release_precision_override: DatePrecision | None
    release_date_override: date | None
    release_date_end_override: date | None
    # The release as this copy shows it (its own values where it has them) …
    release: ReleaseOut
    # … and which of them differ from the catalog: title, cover, edition, region,
    # release_date.
    overrides: list[str]
    format: ItemFormat
    status: ItemStatus
    condition: Condition | None
    completeness: Completeness | None
    play_status: PlayStatus | None
    location: LocationRef | None
    owner: PersonRef | None
    acquired_on: date | None
    purchase_price: Decimal | None
    current_value: Decimal | None
    tags: list[str]
    notes: str
    active_loan: LoanRef | None
    created_at: datetime

    @staticmethod
    def resolve_title(obj: Item) -> str:
        return obj.display_title

    @staticmethod
    def resolve_tags(obj: Item) -> list[str]:
        return sorted(tag.name for tag in obj.tags.all())

    @staticmethod
    def resolve_has_cover_override(obj: Item) -> bool:
        return bool(obj.cover_override)

    @staticmethod
    def resolve_release(obj: Item) -> Any:
        return obj.shown

    @staticmethod
    def resolve_region_override(obj: Item) -> str | None:
        return obj.region_override or None

    @staticmethod
    def resolve_release_precision_override(obj: Item) -> str | None:
        return obj.release_precision_override or None

    @staticmethod
    def resolve_condition(obj: Item) -> str | None:
        return obj.condition or None

    @staticmethod
    def resolve_completeness(obj: Item) -> str | None:
        return obj.completeness or None

    @staticmethod
    def resolve_play_status(obj: Item) -> str | None:
        return obj.play_status or None

    @staticmethod
    def resolve_active_loan(obj: Item) -> object | None:
        """For viewers as the library allows: nothing, or only that it is lent."""
        loan = active_loan(obj)
        shown = getattr(obj, "loan_visibility", "all")
        if loan is None or shown == "all":
            return loan
        if shown == ViewerLoans.STATUS:
            return {"id": loan.pk, "borrower": None, "lent_on": None, "due_on": None}
        return None


class PublicItemOut(Schema):
    """What a public link shows: no prices, notes, people or places."""

    id: UUID
    title: str
    cover_url: str | None
    cover_aspect: float | None
    release: ReleaseOut
    format: ItemFormat
    status: ItemStatus
    completeness: Completeness | None

    @staticmethod
    def resolve_title(obj: Item) -> str:
        return obj.display_title

    @staticmethod
    def resolve_release(obj: Item) -> Any:
        return obj.shown

    @staticmethod
    def resolve_completeness(obj: Item) -> str | None:
        return obj.completeness or None


class ItemIn(Schema):
    release_id: UUID
    format: ItemFormat = ItemFormat.PHYSICAL
    status: ItemStatus = ItemStatus.OWNED
    condition: Condition | None = None
    completeness: Completeness | None = None
    play_status: PlayStatus | None = None
    location_id: UUID | None = None
    owner_id: UUID | None = None
    acquired_on: date | None = None
    purchase_price: Decimal | None = None
    current_value: Decimal | None = None
    tags: list[str] = []
    notes: str = ""
    title_override: str = ""


class ItemPatch(Schema):
    release_id: UUID | None = None
    format: ItemFormat | None = None
    status: ItemStatus | None = None
    condition: Condition | None = None
    completeness: Completeness | None = None
    play_status: PlayStatus | None = None
    location_id: UUID | None = None
    owner_id: UUID | None = None
    acquired_on: date | None = None
    purchase_price: Decimal | None = None
    current_value: Decimal | None = None
    tags: list[str] | None = None
    notes: str | None = None
    # Overrides: "" (or, for the date, an empty precision) resets one to the release's.
    title_override: str | None = None
    edition_override: str | None = None
    region_override: Region | Literal[""] | None = None
    release_precision_override: DatePrecision | Literal[""] | None = None
    release_date_override: date | None = None
    release_date_end_override: date | None = None
