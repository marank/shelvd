from typing import Any
from uuid import UUID

from django.utils.translation import gettext as _
from ninja.errors import HttpError

from ..models import Library, Location


def _parent(
    library: Library, parent_id: UUID | None, moving: Location | None = None
) -> Location | None:
    if not parent_id:
        return None
    parent = Location.objects.filter(pk=parent_id, library=library).first()
    if parent is None:
        raise HttpError(400, _("Unknown location."))
    node: Location | None = parent
    while moving is not None and node is not None:
        if node.pk == moving.pk:
            raise HttpError(400, _("A location cannot be placed inside itself."))
        node = node.parent
    return parent


def create_location(library: Library, data: dict[str, Any]) -> Location:
    name = str(data.get("name", "")).strip()
    if not name:
        raise HttpError(400, _("A name is required."))
    return Location.objects.create(
        library=library,
        parent=_parent(library, data.get("parent_id")),
        name=name,
        kind=data["kind"],
        notes=data.get("notes", ""),
    )


def update_location(location: Location, data: dict[str, Any]) -> Location:
    if "parent_id" in data:
        location.parent = _parent(location.library, data["parent_id"], moving=location)
    for name in ("name", "kind", "notes"):
        if data.get(name) is not None:
            setattr(location, name, data[name])
    location.save()
    return location
