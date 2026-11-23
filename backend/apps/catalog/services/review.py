"""Unreviewed catalog entries: who may change them and how admins approve them."""

from __future__ import annotations

from collections.abc import Iterable

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from ninja.errors import HttpError

from apps.accounts.models import User
from apps.accounts.selectors import is_admin

from ..models import Barcode, Release, ReviewStatus, Work
from ..selectors.review import can_edit


def stamp(entry: Work | Release | Barcode, user: User | None, *, trusted: bool = False) -> None:
    """Set the status of a new entry (before saving it): approved when an admin enters it
    or it comes straight from a source (`trusted`), else pending for review."""
    if isinstance(entry, Work | Release):
        entry.created_by = user
    if user is not None and is_admin(user):
        entry.review_status = ReviewStatus.APPROVED
        entry.reviewed_by = user
        entry.reviewed_at = timezone.now()
    elif trusted:
        entry.review_status = ReviewStatus.APPROVED
    else:
        entry.review_status = ReviewStatus.PENDING


def require_edit(user: User, entry: Work | Release) -> None:
    if not can_edit(user, entry):
        raise HttpError(403, _("Only admins can change the catalog."))


def _approve(entries: Iterable[Work | Release | Barcode], user: User) -> int:
    count = 0
    for entry in entries:
        if entry.pending:
            entry.review_status = ReviewStatus.APPROVED
            entry.reviewed_by = user
            entry.reviewed_at = timezone.now()
            entry.save(update_fields=["review_status", "reviewed_by", "reviewed_at", "updated_at"])
            count += 1
    return count


@transaction.atomic
def approve(
    user: User,
    *,
    works: Iterable[Work] = (),
    releases: Iterable[Release] = (),
    barcodes: Iterable[Barcode] = (),
) -> int:
    """Approve entries; a release takes its unreviewed game along."""
    releases = list(releases)
    count = _approve(releases, user)
    count += _approve([*works, *{r.work_id: r.work for r in releases}.values()], user)
    return count + _approve(barcodes, user)
