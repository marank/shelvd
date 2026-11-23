"""What a library's viewers don't see: people's contact details, money and – as the owner
chooses – loans entirely or everything about them but whether a copy is lent."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from apps.accounts.models import User

from ..models import Item, Library
from .access import role_in

MONEY_FIELDS = {"copy.price", "copy.value"}
# Borrower and dates: never for viewers, whatever the loan setting.
LOAN_FIELDS = {"loan.to", "loan.since", "loan.due", "loan.overdue"}


@dataclass(frozen=True)
class Visibility:
    full: bool  # owner or editor
    loans: str  # "all" | ViewerLoans


def visibility(library: Library, user: User) -> Visibility:
    if role_in(library, user) in ("owner", "editor"):
        return Visibility(full=True, loans="all")
    return Visibility(full=False, loans=library.viewer_loans)


def hidden_fields(seen: Visibility) -> set[str]:
    """Field keys a viewer can't group, sort or filter by (they would give values away)."""
    if seen.full:
        return set()
    return MONEY_FIELDS | LOAN_FIELDS


def allowed(keys: Iterable[str], seen: Visibility) -> list[str]:
    hidden = hidden_fields(seen)
    return [key for key in keys if key not in hidden]


def allowed_sort(sort: str, seen: Visibility) -> str:
    """ "copy.price,-game.title" → "-game.title" for viewers."""
    hidden = hidden_fields(seen)
    parts = [p for p in sort.split(",") if p.strip().lstrip("-") not in hidden]
    return ",".join(parts) or "game.title"


def redact(items: Iterable[Item], seen: Visibility) -> None:
    """Blank what viewers don't see on loaded copies (never saved)."""
    if seen.full:
        return
    for item in items:
        item.purchase_price = None
        item.current_value = None
        item.loan_visibility = seen.loans
