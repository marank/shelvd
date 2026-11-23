import re
from uuid import UUID

from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from ninja import Router, Status
from ninja.errors import HttpError

from apps.accounts.api.auth import current_user
from apps.core.api.errors import ErrorOut

from ..models import Overview
from ..schemas import OverviewIn, OverviewOut, OverviewPatch
from ..selectors.conditions import parse_conditions
from ..selectors.filters import check_fields
from ..selectors.sorting import parse_sort
from ..services.access import get_library

router = Router(tags=["overviews"])
ERRORS = {400: ErrorOut, 403: ErrorOut, 404: ErrorOut}


FIELD_KEY = re.compile(r"^[a-z]+\.[a-z_]{1,40}$")
PRESENTATIONS = {"grid", "list", "table", "detail"}


def _validate(
    group_by: list[str] | None,
    filters: list[str] | None,
    sort: str | None,
    fields: dict[str, list[str]] | None = None,
    section: str | None = None,
) -> None:
    check_fields(list(group_by or []) + ([section] if section else []))
    parse_conditions(filters or [])
    # Display fields live in the frontend's registry; unknown keys are simply not shown.
    for presentation, keys in (fields or {}).items():
        if (
            presentation not in PRESENTATIONS
            or len(keys) > 40
            or not all(FIELD_KEY.match(key) for key in keys)
        ):
            raise HttpError(400, _("Invalid fields."))
    if sort is not None:
        parse_sort(sort)


@router.get("{library_id}/overviews", response={200: list[OverviewOut], **ERRORS})
def list_overviews(request: HttpRequest, library_id: UUID) -> QuerySet[Overview]:
    user = current_user(request)
    return Overview.objects.filter(library=get_library(user, library_id), user=user)


@router.post("{library_id}/overviews", response={201: OverviewOut, **ERRORS})
def create_overview(
    request: HttpRequest, library_id: UUID, payload: OverviewIn
) -> Status[Overview]:
    user = current_user(request)
    library = get_library(user, library_id)
    _validate(payload.group_by, payload.filters, payload.sort, payload.fields, payload.section)
    if not payload.name.strip():
        raise HttpError(400, _("A name is required."))
    return Status(201, Overview.objects.create(library=library, user=user, **payload.model_dump()))


@router.patch("{library_id}/overviews/{overview_id}", response={200: OverviewOut, **ERRORS})
def update_overview(
    request: HttpRequest, library_id: UUID, overview_id: UUID, payload: OverviewPatch
) -> Overview:
    user = current_user(request)
    overview = get_object_or_404(
        Overview, pk=overview_id, library=get_library(user, library_id), user=user
    )
    _validate(payload.group_by, payload.filters, payload.sort, payload.fields, payload.section)
    for name, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(overview, name, value)
    overview.save()
    return overview


@router.delete("{library_id}/overviews/{overview_id}", response={204: None, **ERRORS})
def delete_overview(request: HttpRequest, library_id: UUID, overview_id: UUID) -> Status[None]:
    user = current_user(request)
    get_object_or_404(
        Overview, pk=overview_id, library=get_library(user, library_id), user=user
    ).delete()
    return Status(204, None)
