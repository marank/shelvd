"""App-wide roles: admins (`is_staff`) look after the shared catalog."""

from __future__ import annotations

from django.utils.translation import gettext as _
from ninja.errors import HttpError

from ..models import User


def is_admin(user: User) -> bool:
    return bool(user.is_staff)


def require_admin(user: User) -> None:
    if not is_admin(user):
        raise HttpError(403, _("Only admins can change the catalog."))
