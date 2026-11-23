from uuid import UUID

from ninja import Schema

from ..models import Location, LocationKind


class LocationOut(Schema):
    id: UUID
    parent_id: UUID | None
    name: str
    kind: LocationKind
    notes: str
    path: str
    item_count: int = 0


class LocationStep(Schema):
    name: str
    kind: LocationKind


class LocationRef(Schema):
    id: UUID
    name: str
    path: str
    # Outermost first (room › shelf › box), so clients can show "the box" or "the room".
    trail: list[LocationStep]

    @staticmethod
    def resolve_trail(obj: Location) -> list[dict[str, str]]:
        steps: list[dict[str, str]] = []
        node: Location | None = obj
        seen: set[object] = set()
        while node is not None and node.pk not in seen:
            seen.add(node.pk)
            steps.append({"name": node.name, "kind": node.kind})
            node = node.parent
        return list(reversed(steps))


class LocationIn(Schema):
    name: str
    parent_id: UUID | None = None
    kind: LocationKind = LocationKind.OTHER
    notes: str = ""


class LocationPatch(Schema):
    name: str | None = None
    parent_id: UUID | None = None
    kind: LocationKind | None = None
    notes: str | None = None
