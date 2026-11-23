from __future__ import annotations

from typing import Any
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.translation import gettext as _
from ninja.errors import HttpError

from apps.accounts.models import User
from apps.catalog.models import Release
from apps.collection.models import Item, ItemStatus, Library
from apps.collection.schemas import ItemIn
from apps.collection.services.access import get_library, visible_libraries
from apps.collection.services.items import create_item

from ..models import Tracking
from ..schemas import TakeOverIn, TrackingIn, TrackingPatch


def visible_trackings(user: User) -> QuerySet[Tracking]:
    """Own entries plus those aimed at a library the user can see."""
    return Tracking.objects.filter(Q(user=user) | Q(library__in=visible_libraries(user))).distinct()


def owned_in(user: User, release_ids: list[UUID]) -> dict[UUID, list[Library]]:
    """Per release: the libraries the user can see that already own a copy of it."""
    result: dict[UUID, list[Library]] = {}
    items = (
        Item.objects.filter(
            release_id__in=release_ids,
            status=ItemStatus.OWNED,
            library__in=visible_libraries(user),
        )
        .select_related("library")
        .order_by("library__name")
    )
    for item in items:
        libraries = result.setdefault(item.release_id, [])
        if item.library not in libraries:
            libraries.append(item.library)
    return result


def _target(user: User, library_id: UUID | None) -> Library | None:
    """Showing an entry to a library's members takes editing rights there."""
    return get_library(user, library_id, need="editor") if library_id else None


def create_tracking(user: User, data: TrackingIn) -> Tracking:
    release = Release.objects.filter(pk=data.release_id).first()
    if release is None:
        raise HttpError(400, _("Unknown release."))
    values: dict[str, Any] = data.model_dump(exclude={"release_id", "library_id"})
    try:
        with transaction.atomic():
            return Tracking.objects.create(
                user=user, release=release, library=_target(user, data.library_id), **values
            )
    except IntegrityError as exc:
        raise HttpError(409, _("You already track this release.")) from exc


def update_tracking(tracking: Tracking, data: TrackingPatch) -> Tracking:
    fields = data.model_dump(exclude_unset=True)
    if "library_id" in fields:
        tracking.library = _target(tracking.user, fields.pop("library_id"))
    for name in ("price", "ordered_on"):  # may be cleared
        if name in fields:
            setattr(tracking, name, fields.pop(name))
    for name, value in fields.items():
        if value is not None:
            setattr(tracking, name, value)
    tracking.save()
    return tracking


@transaction.atomic
def take_over(tracking: Tracking, user: User, data: TakeOverIn) -> Item:
    """Turn the entry into a copy in a library and remove it from tracking."""
    library = get_library(user, data.library_id, need="editor")
    item = create_item(
        library,
        ItemIn(
            release_id=tracking.release_id,
            format=data.format,
            condition=data.condition,
            completeness=data.completeness,
            location_id=data.location_id,
            owner_id=data.owner_id,
            acquired_on=data.acquired_on or tracking.ordered_on or timezone.localdate(),
            purchase_price=tracking.price,
            notes="\n".join(n for n in (tracking.notes, data.notes) if n),
        ),
    )
    tracking.delete()
    return item
