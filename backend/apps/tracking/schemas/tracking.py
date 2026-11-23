from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from ninja import Schema

from apps.catalog.schemas import ReleaseOut
from apps.collection.models import Completeness, Condition, ItemFormat

from ..models import Tracking, TrackingStatus


class LibraryRef(Schema):
    id: UUID
    name: str


class TrackingOut(Schema):
    id: UUID
    release: ReleaseOut
    status: TrackingStatus
    library: LibraryRef | None
    user: str
    is_mine: bool  # set per request by the API
    # Libraries you can see that already own a copy of the release (set per request).
    owned_in: list[LibraryRef]
    shop: str
    price: Decimal | None
    ordered_on: date | None
    notes: str
    created_at: datetime

    @staticmethod
    def resolve_user(obj: Tracking) -> str:
        return obj.user.get_username()


class TrackingIn(Schema):
    release_id: UUID
    status: TrackingStatus = TrackingStatus.WATCHING
    library_id: UUID | None = None
    shop: str = ""
    price: Decimal | None = None
    ordered_on: date | None = None
    notes: str = ""


class TrackingPatch(Schema):
    status: TrackingStatus | None = None
    library_id: UUID | None = None
    shop: str | None = None
    price: Decimal | None = None
    ordered_on: date | None = None
    notes: str | None = None


class TakeOverIn(Schema):
    """The game arrived: create the copy in a library (price and date come along)."""

    library_id: UUID
    format: ItemFormat = ItemFormat.PHYSICAL
    condition: Condition | None = None
    completeness: Completeness | None = None
    location_id: UUID | None = None
    owner_id: UUID | None = None
    acquired_on: date | None = None
    notes: str = ""
