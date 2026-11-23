from uuid import UUID

from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Status

from apps.accounts.api.auth import current_user
from apps.accounts.models import User
from apps.collection.schemas import ItemOut
from apps.collection.selectors.items import base_queryset
from apps.core.api.errors import ErrorOut

from ..models import Tracking
from ..schemas import TakeOverIn, TrackingIn, TrackingOut, TrackingPatch
from ..services import tracking as service

router = Router(tags=["tracking"])
ERRORS = {400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 409: ErrorOut}


def trackings() -> QuerySet[Tracking]:
    return Tracking.objects.select_related(
        "user", "library", "release__work", "release__platform", "release__publisher"
    ).prefetch_related(
        "release__work__genres",
        "release__work__developers",
        "release__developers",
        "release__work__series",
        "release__work__franchises",
        "release__barcodes",
    )


def mark(entries: list[Tracking], user: User) -> list[Tracking]:
    """The models, marked for TrackingOut.is_mine and .owned_in (one query for all)."""
    owned = service.owned_in(user, [t.release_id for t in entries])
    for tracking in entries:
        tracking.is_mine = tracking.user_id == user.pk  # type: ignore[attr-defined]
        tracking.owned_in = owned.get(tracking.release_id, [])  # type: ignore[attr-defined]
        if tracking.user_id != user.pk:
            # Someone else's entry: the game and its status, not where or for how much.
            tracking.shop, tracking.price, tracking.ordered_on, tracking.notes = "", None, None, ""
    return entries


def out(tracking: Tracking, user: User) -> Tracking:
    return mark([tracking], user)[0]


def own(request: HttpRequest, tracking_id: UUID) -> Tracking:
    return get_object_or_404(trackings(), pk=tracking_id, user=current_user(request))


@router.get("", response=list[TrackingOut])
def list_trackings(
    request: HttpRequest,
    mine: bool = False,
    work: UUID | None = None,
    library: UUID | None = None,
) -> list[Tracking]:
    """Own entries and those aimed at libraries you can see, by release date."""
    user = current_user(request)
    queryset = trackings().filter(pk__in=service.visible_trackings(user).values("pk"))
    if mine:
        queryset = queryset.filter(user=user)
    if work is not None:
        queryset = queryset.filter(release__work_id=work)
    if library is not None:
        queryset = queryset.filter(library_id=library)
    return mark(list(queryset.order_by("release__sort_date", "created_at")), user)


@router.post("", response={201: TrackingOut, **ERRORS})
def create_tracking(request: HttpRequest, payload: TrackingIn) -> Status[Tracking]:
    user = current_user(request)
    tracking = service.create_tracking(user, payload)
    return Status(201, out(trackings().get(pk=tracking.pk), user))


@router.get("{tracking_id}", response={200: TrackingOut, **ERRORS})
def get_tracking(request: HttpRequest, tracking_id: UUID) -> Tracking:
    user = current_user(request)
    visible = service.visible_trackings(user).values("pk")
    return out(get_object_or_404(trackings().filter(pk__in=visible), pk=tracking_id), user)


@router.patch("{tracking_id}", response={200: TrackingOut, **ERRORS})
def update_tracking(request: HttpRequest, tracking_id: UUID, payload: TrackingPatch) -> Tracking:
    tracking = service.update_tracking(own(request, tracking_id), payload)
    return out(trackings().get(pk=tracking.pk), current_user(request))


@router.delete("{tracking_id}", response={204: None, **ERRORS})
def delete_tracking(request: HttpRequest, tracking_id: UUID) -> Status[None]:
    own(request, tracking_id).delete()
    return Status(204, None)


@router.post("{tracking_id}/take-over", response={201: ItemOut, **ERRORS})
def take_over(request: HttpRequest, tracking_id: UUID, payload: TakeOverIn) -> Status[object]:
    """The game arrived: it becomes a copy in the chosen library."""
    user = current_user(request)
    item = service.take_over(own(request, tracking_id), user, payload)
    return Status(201, base_queryset(item.library).get(pk=item.pk))
