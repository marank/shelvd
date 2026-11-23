from uuid import UUID

from django.db.models import Count
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Status

from apps.accounts.api.auth import current_user
from apps.core.api.errors import ErrorOut

from ..models import Location, LocationKind
from ..schemas import LocationIn, LocationOut, LocationPatch
from ..services import locations as service
from ..services.access import get_library

router = Router(tags=["locations"])
ERRORS = {400: ErrorOut, 403: ErrorOut, 404: ErrorOut}


def location_out(location: Location) -> LocationOut:
    return LocationOut(
        id=location.pk,
        parent_id=location.parent_id,
        name=location.name,
        kind=LocationKind(location.kind),
        notes=location.notes,
        path=location.path,
        item_count=getattr(location, "item_count", 0),
    )


@router.get("{library_id}/locations", response={200: list[LocationOut], **ERRORS})
def list_locations(request: HttpRequest, library_id: UUID) -> list[LocationOut]:
    library = get_library(current_user(request), library_id)
    locations = list(library.locations.annotate(item_count=Count("items")))
    by_id = {location.pk: location for location in locations}
    for location in locations:  # resolve paths without a query per level
        if location.parent_id:
            location.parent = by_id.get(location.parent_id)
    return sorted((location_out(loc) for loc in locations), key=lambda loc: loc.path.lower())


@router.post("{library_id}/locations", response={201: LocationOut, **ERRORS})
def create_location(
    request: HttpRequest, library_id: UUID, payload: LocationIn
) -> Status[LocationOut]:
    library = get_library(current_user(request), library_id, need="editor")
    return Status(201, location_out(service.create_location(library, payload.model_dump())))


@router.patch("{library_id}/locations/{location_id}", response={200: LocationOut, **ERRORS})
def update_location(
    request: HttpRequest, library_id: UUID, location_id: UUID, payload: LocationPatch
) -> LocationOut:
    library = get_library(current_user(request), library_id, need="editor")
    location = get_object_or_404(Location, pk=location_id, library=library)
    data = payload.model_dump(exclude_unset=True)
    return location_out(service.update_location(location, data))


@router.delete("{library_id}/locations/{location_id}", response={204: None, **ERRORS})
def delete_location(request: HttpRequest, library_id: UUID, location_id: UUID) -> Status[None]:
    """Items inside keep existing, just without a location; sub-locations go with it."""
    library = get_library(current_user(request), library_id, need="editor")
    get_object_or_404(Location, pk=location_id, library=library).delete()
    return Status(204, None)
