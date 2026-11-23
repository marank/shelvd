"""Admins review what people entered themselves (mounted under /catalog)."""

from uuid import UUID

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Status

from apps.accounts.api.auth import current_user
from apps.accounts.selectors import require_admin
from apps.core.api.errors import ErrorOut

from ..models import Barcode, Release, Work
from ..schemas.review import ApprovedOut, ApproveIn, ReviewQueueOut
from ..selectors.review import pending_count, review_queue
from ..services import review

router = Router(tags=["review"])
ERRORS = {403: ErrorOut, 404: ErrorOut}


@router.get("review", response={200: ReviewQueueOut, **ERRORS})
def queue(request: HttpRequest) -> ReviewQueueOut:
    require_admin(current_user(request))
    entries = review_queue()
    return ReviewQueueOut(count=len(entries), entries=entries)  # type: ignore[arg-type]


@router.get("review/count", response={200: dict[str, int], **ERRORS})
def count(request: HttpRequest) -> dict[str, int]:
    """For the admins' sidebar badge."""
    require_admin(current_user(request))
    return {"count": pending_count()}


@router.post("review/approve", response={200: ApprovedOut, **ERRORS})
def approve(request: HttpRequest, payload: ApproveIn) -> ApprovedOut:
    user = current_user(request)
    require_admin(user)
    approved = review.approve(
        user,
        works=Work.objects.filter(pk__in=payload.works),
        releases=Release.objects.filter(pk__in=payload.releases).select_related("work"),
        barcodes=Barcode.objects.filter(pk__in=payload.barcodes),
    )
    return ApprovedOut(approved=approved)


@router.delete("barcodes/{barcode_id}", response={204: None, **ERRORS})
def delete_barcode(request: HttpRequest, barcode_id: UUID) -> Status[None]:
    """A wrong assignment: the next scan of the code asks again."""
    require_admin(current_user(request))
    get_object_or_404(Barcode, pk=barcode_id).delete()
    return Status(204, None)
