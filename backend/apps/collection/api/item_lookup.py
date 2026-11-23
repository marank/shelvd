"""One copy by its id alone (mounted under /api/items): links to a copy don't need to
name its library – the answer says which one it is."""

from uuid import UUID

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router

from apps.accounts.api.auth import current_user
from apps.core.api.errors import ErrorOut

from ..models import Item
from ..schemas import ItemOut
from ..selectors.items import base_queryset
from ..services.access import get_library
from ..services.visibility import redact, visibility

router = Router(tags=["items"])


@router.get("{item_id}", response={200: ItemOut, 404: ErrorOut})
def get_item_by_id(request: HttpRequest, item_id: UUID) -> Item:
    # Same 404 for unknown copies and copies of libraries the user can't see.
    library_id = get_object_or_404(Item.objects.only("library_id"), pk=item_id).library_id
    user = current_user(request)
    library = get_library(user, library_id)
    item = get_object_or_404(base_queryset(library), pk=item_id)
    redact([item], visibility(library, user))
    return item
