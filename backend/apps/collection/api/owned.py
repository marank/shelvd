from uuid import UUID

from django.http import HttpRequest
from ninja import Router

from apps.accounts.api.auth import current_user
from apps.core.api.errors import ErrorOut

from ..schemas import OwnedReleaseOut
from ..selectors.owned import OwnedRelease, owned_releases
from ..services.access import get_library

router = Router(tags=["items"])


@router.get("{library_id}/owned", response={200: list[OwnedReleaseOut], 404: ErrorOut})
def list_owned(request: HttpRequest, library_id: UUID) -> list[OwnedRelease]:
    """The library's releases with owned copies, by id – catalog pages and the add dialog
    mark them."""
    return owned_releases(get_library(current_user(request), library_id))
