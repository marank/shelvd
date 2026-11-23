from decimal import Decimal
from typing import Literal
from uuid import UUID

from django.conf import settings
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import File, P, Query, QueryEx, Router, Status, UploadedFile

from apps.accounts.api.auth import current_user
from apps.core.api.errors import ErrorOut
from apps.providers.schemas import CoverIn

from ..models import Item
from ..schemas import GroupNodeOut, ItemIn, ItemOut, ItemPageOut, ItemPatch, TreeOut
from ..selectors.conditions import Condition, parse_conditions
from ..selectors.filters import check_fields, parse_filters
from ..selectors.grouping import Node, Section, build_tree, split_sections
from ..selectors.items import base_queryset, list_items
from ..services import items as service
from ..services.access import get_library
from ..services.visibility import Visibility, allowed, allowed_sort, redact, visibility

router = Router(tags=["items"])
ERRORS = {400: ErrorOut, 403: ErrorOut, 404: ErrorOut}


def node_out(node: Node) -> GroupNodeOut:
    return GroupNodeOut(
        field=node.field,
        key=node.key,
        label=node.label,
        count=node.count,
        value=node.value,
        children=[node_out(child) for child in node.children],
    )


@router.get("{library_id}/items", response={200: ItemPageOut, **ERRORS})
def items(
    request: HttpRequest,
    library_id: UUID,
    q: str = "",
    filters: QueryEx[list[str] | None, P(alias="filter")] = None,
    where: Query[list[str] | None] = None,
    match: Literal["all", "any"] = "all",
    sort: str = "game.title",
    limit: int = 100,
    offset: int = 0,
    work: UUID | None = None,
    section: str = "",
) -> dict[str, object]:
    """Items of a library. `filter=field:value` (repeatable) narrows to a group of the
    tree; `where` are a view's conditions (selectors.conditions), all or any of them per
    `match`; `q` searches all fields including barcodes; `work` limits to one game.
    `section` (a grouping field) orders the list by its groups and returns their headings;
    an item in several groups is listed in each."""
    user = current_user(request)
    library = get_library(user, library_id)
    seen = visibility(library, user)
    found = list_items(
        library,
        query=q,
        filters=_filters(filters, seen),
        conditions=_conditions(where, seen),
        any_of=match == "any",
        sort=allowed_sort(sort, seen),
    )
    if work is not None:
        found = [item for item in found if item.release.work_id == work]
    sections: list[Section] = []
    if section and allowed([section], seen):
        found, sections = split_sections(found, check_fields([section])[0])
    limit = max(1, min(limit, 500))
    page = found[offset : offset + limit]
    redact(page, seen)
    return {"count": len(found), "items": page, "sections": sections}


def _filters(raw: list[str] | None, seen: Visibility) -> dict[str, list[str]]:
    """A viewer's filters on hidden fields (money, loans) are dropped, not answered."""
    parsed = parse_filters(raw or [])
    return {field: keys for field, keys in parsed.items() if allowed([field], seen)}


def _conditions(raw: list[str] | None, seen: Visibility) -> list[Condition]:
    return [c for c in parse_conditions(raw or []) if allowed([c.field], seen)]


@router.get("{library_id}/tree", response={200: TreeOut, **ERRORS})
def tree(
    request: HttpRequest,
    library_id: UUID,
    group_by: Query[list[str] | None] = None,
    q: str = "",
    filters: QueryEx[list[str] | None, P(alias="filter")] = None,
    where: Query[list[str] | None] = None,
    match: Literal["all", "any"] = "all",
) -> TreeOut:
    """Nested groups with counts, e.g. group_by=platform&group_by=publisher&group_by=year."""
    user = current_user(request)
    library = get_library(user, library_id)
    seen = visibility(library, user)
    found = list_items(
        library,
        query=q,
        filters=_filters(filters, seen),
        conditions=_conditions(where, seen),
        any_of=match == "any",
    )
    nodes = build_tree(found, check_fields(allowed(group_by or [], seen)))
    redact(found, seen)
    return TreeOut(
        total=len(found),
        total_value=sum((item.current_value or Decimal(0) for item in found), Decimal(0)),
        group_by=group_by or [],
        nodes=[node_out(n) for n in nodes],
    )


@router.post("{library_id}/items", response={201: ItemOut, **ERRORS})
def create_item(request: HttpRequest, library_id: UUID, payload: ItemIn) -> Status[Item]:
    library = get_library(current_user(request), library_id, need="editor")
    item = service.create_item(library, payload)
    return Status(201, base_queryset(library).get(pk=item.pk))


@router.get("{library_id}/items/{item_id}", response={200: ItemOut, **ERRORS})
def get_item(request: HttpRequest, library_id: UUID, item_id: UUID) -> Item:
    user = current_user(request)
    library = get_library(user, library_id)
    item = get_object_or_404(base_queryset(library), pk=item_id)
    redact([item], visibility(library, user))
    return item


@router.patch("{library_id}/items/{item_id}", response={200: ItemOut, **ERRORS})
def update_item(request: HttpRequest, library_id: UUID, item_id: UUID, payload: ItemPatch) -> Item:
    library = get_library(current_user(request), library_id, need="editor")
    item = get_object_or_404(Item, pk=item_id, library=library)
    service.update_item(item, payload)
    return base_queryset(library).get(pk=item.pk)


@router.delete("{library_id}/items/{item_id}", response={204: None, **ERRORS})
def delete_item(request: HttpRequest, library_id: UUID, item_id: UUID) -> Status[None]:
    library = get_library(current_user(request), library_id, need="editor")
    service.delete_item(get_object_or_404(Item, pk=item_id, library=library))
    return Status(204, None)


@router.post("{library_id}/items/{item_id}/cover", response={200: ItemOut, **ERRORS})
def upload_item_cover(
    request: HttpRequest, library_id: UUID, item_id: UUID, file: File[UploadedFile]
) -> Item:
    library = get_library(current_user(request), library_id, need="editor")
    item = get_object_or_404(Item, pk=item_id, library=library)
    service.set_item_cover(item, file, settings.COVER_MAX_MB)
    return base_queryset(library).get(pk=item.pk)


@router.post(
    "{library_id}/items/{item_id}/cover-from", response={200: ItemOut, 502: ErrorOut, **ERRORS}
)
def item_cover_from(
    request: HttpRequest, library_id: UUID, item_id: UUID, payload: CoverIn
) -> Item:
    """Own cover for this copy, taken from a covers source (a cover-candidates token)."""
    library = get_library(current_user(request), library_id, need="editor")
    item = get_object_or_404(Item, pk=item_id, library=library)
    service.set_item_cover_from(item, payload.token, settings.COVER_MAX_MB)
    return base_queryset(library).get(pk=item.pk)


@router.post("{library_id}/items/{item_id}/reset", response={200: ItemOut, **ERRORS})
def reset_item(request: HttpRequest, library_id: UUID, item_id: UUID) -> Item:
    """Drop everything this copy shows differently from its release."""
    library = get_library(current_user(request), library_id, need="editor")
    item = get_object_or_404(Item, pk=item_id, library=library)
    service.reset_overrides(item)
    return base_queryset(library).get(pk=item.pk)


@router.delete("{library_id}/items/{item_id}/cover", response={200: ItemOut, **ERRORS})
def remove_item_cover(request: HttpRequest, library_id: UUID, item_id: UUID) -> Item:
    library = get_library(current_user(request), library_id, need="editor")
    item = get_object_or_404(Item, pk=item_id, library=library)
    service.set_item_cover(item, None, settings.COVER_MAX_MB)
    return base_queryset(library).get(pk=item.pk)
