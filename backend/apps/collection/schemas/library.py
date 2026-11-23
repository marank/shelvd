from datetime import datetime
from uuid import UUID

from ninja import Schema

from ..models import Role, ViewerLoans


class LibraryOut(Schema):
    id: UUID
    name: str
    description: str
    owner: str
    role: str  # owner | editor | viewer — set by the API per request
    item_count: int
    public_token: str | None  # only for the owner
    viewer_loans: ViewerLoans  # what viewers see of loans
    created_at: datetime


class LibraryIn(Schema):
    name: str
    description: str = ""


class LibraryPatch(Schema):
    name: str | None = None
    description: str | None = None
    viewer_loans: ViewerLoans | None = None


class MemberOut(Schema):
    id: UUID
    username: str
    role: Role


class MemberIn(Schema):
    username: str
    role: Role = Role.VIEWER


class MemberPatch(Schema):
    role: Role
