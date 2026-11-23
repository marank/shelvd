from uuid import UUID

from django.db.models import Count, QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from ninja import Router, Status
from ninja.errors import HttpError

from apps.accounts.api.auth import current_user
from apps.core.api.errors import ErrorOut

from ..models import CustomList, ListEntry
from ..schemas import EntryIn, EntryOut, EntryPatch, ListIn, ListOut, ListPatch
from ..services import lists as service

router = Router(tags=["lists"])
ERRORS = {400: ErrorOut, 404: ErrorOut, 409: ErrorOut}


def entries(custom_list: CustomList) -> QuerySet[ListEntry]:
    return custom_list.entries.select_related(
        "release__work", "release__platform", "release__publisher"
    ).prefetch_related(
        "release__work__genres",
        "release__work__developers",
        "release__developers",
        "release__work__series",
        "release__work__franchises",
        "release__barcodes",
    )


def list_out(custom_list: CustomList) -> ListOut:
    count = getattr(custom_list, "entry_count", None)
    return ListOut(
        id=custom_list.pk,
        name=custom_list.name,
        description=custom_list.description,
        owner=custom_list.owner.get_username(),
        public_token=custom_list.public_token,
        entry_count=count if count is not None else custom_list.entries.count(),
        created_at=custom_list.created_at,
    )


def own_list(request: HttpRequest, list_id: UUID) -> CustomList:
    return get_object_or_404(
        CustomList.objects.select_related("owner"), pk=list_id, owner=current_user(request)
    )


@router.get("", response=list[ListOut])
def list_lists(request: HttpRequest) -> list[ListOut]:
    lists = (
        CustomList.objects.filter(owner=current_user(request))
        .select_related("owner")
        .annotate(entry_count=Count("entries"))
    )
    return [list_out(item) for item in lists]


@router.post("", response={201: ListOut, **ERRORS})
def create_list(request: HttpRequest, payload: ListIn) -> Status[ListOut]:
    if not payload.name.strip():
        raise HttpError(400, _("A name is required."))
    custom_list = CustomList.objects.create(
        owner=current_user(request), name=payload.name.strip(), description=payload.description
    )
    return Status(201, list_out(custom_list))


@router.get("{list_id}", response={200: ListOut, **ERRORS})
def get_list(request: HttpRequest, list_id: UUID) -> ListOut:
    return list_out(own_list(request, list_id))


@router.patch("{list_id}", response={200: ListOut, **ERRORS})
def update_list(request: HttpRequest, list_id: UUID, payload: ListPatch) -> ListOut:
    custom_list = own_list(request, list_id)
    for name, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(custom_list, name, value)
    custom_list.save()
    return list_out(custom_list)


@router.delete("{list_id}", response={204: None, **ERRORS})
def delete_list(request: HttpRequest, list_id: UUID) -> Status[None]:
    own_list(request, list_id).delete()
    return Status(204, None)


@router.post("{list_id}/public-link", response={200: ListOut, **ERRORS})
def enable_public_link(request: HttpRequest, list_id: UUID) -> ListOut:
    return list_out(service.toggle_public(own_list(request, list_id), True))


@router.delete("{list_id}/public-link", response={200: ListOut, **ERRORS})
def disable_public_link(request: HttpRequest, list_id: UUID) -> ListOut:
    return list_out(service.toggle_public(own_list(request, list_id), False))


@router.get("{list_id}/entries", response={200: list[EntryOut], **ERRORS})
def list_entries(request: HttpRequest, list_id: UUID) -> QuerySet[ListEntry]:
    return entries(own_list(request, list_id))


@router.post("{list_id}/entries", response={201: EntryOut, **ERRORS})
def add_entry(request: HttpRequest, list_id: UUID, payload: EntryIn) -> Status[ListEntry]:
    custom_list = own_list(request, list_id)
    entry = service.add_entry(custom_list, payload, current_user(request))
    return Status(201, entries(custom_list).get(pk=entry.pk))


@router.patch("{list_id}/entries/{entry_id}", response={200: EntryOut, **ERRORS})
def update_entry(
    request: HttpRequest, list_id: UUID, entry_id: UUID, payload: EntryPatch
) -> ListEntry:
    custom_list = own_list(request, list_id)
    entry = get_object_or_404(ListEntry, pk=entry_id, custom_list=custom_list)
    for name, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(entry, name, value)
    entry.save()
    return entries(custom_list).get(pk=entry.pk)


@router.delete("{list_id}/entries/{entry_id}", response={204: None, **ERRORS})
def remove_entry(request: HttpRequest, list_id: UUID, entry_id: UUID) -> Status[None]:
    custom_list = own_list(request, list_id)
    get_object_or_404(ListEntry, pk=entry_id, custom_list=custom_list).delete()
    return Status(204, None)
