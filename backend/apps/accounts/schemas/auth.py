from typing import Any
from uuid import UUID

from ninja import Schema


class UserOut(Schema):
    id: UUID
    username: str
    email: str
    is_staff: bool
    # May add games to the catalog (unreviewed): admins and library editors.
    can_contribute: bool

    @staticmethod
    def resolve_can_contribute(obj: Any) -> bool:
        from apps.collection.services.access import can_contribute

        return can_contribute(obj)


class LoginIn(Schema):
    username: str
    password: str


class RegisterIn(Schema):
    username: str
    email: str = ""
    password: str
