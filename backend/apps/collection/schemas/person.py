from uuid import UUID

from ninja import Schema


class PersonOut(Schema):
    id: UUID
    name: str
    email: str
    notes: str
    open_loans: int = 0


class PersonRef(Schema):
    id: UUID
    name: str


class PersonIn(Schema):
    name: str
    email: str = ""
    notes: str = ""


class PersonPatch(Schema):
    name: str | None = None
    email: str | None = None
    notes: str | None = None
