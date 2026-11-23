from datetime import date
from uuid import UUID

from django.utils import timezone
from ninja import Schema

from ..models import Loan
from .person import PersonRef


class LoanRef(Schema):
    """Viewers may only learn that a copy is lent: then borrower and date are empty."""

    id: UUID
    borrower: PersonRef | None
    lent_on: date | None
    due_on: date | None


class LoanOut(Schema):
    id: UUID
    item_id: UUID
    item_title: str
    platform: str
    cover_url: str | None
    cover_aspect: float | None
    borrower: PersonRef
    lent_on: date
    due_on: date | None
    returned_on: date | None
    notes: str
    overdue: bool

    @staticmethod
    def resolve_item_title(obj: Loan) -> str:
        return obj.item.display_title

    @staticmethod
    def resolve_platform(obj: Loan) -> str:
        platform = obj.item.release.platform
        return platform.short_name or platform.name

    @staticmethod
    def resolve_cover_url(obj: Loan) -> str | None:
        return obj.item.cover_url

    @staticmethod
    def resolve_cover_aspect(obj: Loan) -> float | None:
        return obj.item.cover_aspect

    @staticmethod
    def resolve_overdue(obj: Loan) -> bool:
        return bool(obj.returned_on is None and obj.due_on and obj.due_on < timezone.localdate())


class LoanIn(Schema):
    """Lend an item: either an existing person or a new name."""

    item_id: UUID
    borrower_id: UUID | None = None
    borrower_name: str = ""
    lent_on: date | None = None
    due_on: date | None = None
    notes: str = ""


class LoanReturnIn(Schema):
    returned_on: date | None = None
