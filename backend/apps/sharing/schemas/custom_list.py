from datetime import datetime
from uuid import UUID

from ninja import Schema

from apps.catalog.schemas import ReleaseOut


class EntryOut(Schema):
    id: UUID
    release: ReleaseOut
    item_id: UUID | None
    note: str
    position: int


class ListOut(Schema):
    id: UUID
    name: str
    description: str
    owner: str
    public_token: str | None
    entry_count: int
    created_at: datetime


class PublicListOut(Schema):
    name: str
    description: str
    owner: str
    entries: list[EntryOut]


class ListIn(Schema):
    name: str
    description: str = ""


class ListPatch(Schema):
    name: str | None = None
    description: str | None = None


class EntryIn(Schema):
    release_id: UUID
    item_id: UUID | None = None
    note: str = ""


class EntryPatch(Schema):
    note: str | None = None
    position: int | None = None
