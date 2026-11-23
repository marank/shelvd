"""Who may see and change a library. Owner: everything; editor: content; viewer: read."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from django.db.models import Q, QuerySet
from django.utils.translation import gettext as _
from ninja.errors import HttpError

from apps.accounts.models import User
from apps.accounts.selectors import is_admin

from ..models import Library, LibraryMember, Role

Need = Literal["viewer", "editor", "owner"]


def visible_libraries(user: User) -> QuerySet[Library]:
    return Library.objects.filter(Q(owner=user) | Q(members__user=user)).distinct()


def role_in(library: Library, user: User) -> str | None:
    """ "owner", "editor", "viewer" or None."""
    if library.owner_id == user.pk:
        return "owner"
    member = LibraryMember.objects.filter(library=library, user=user).first()
    return member.role if member else None


def get_library(user: User, library_id: UUID, *, need: Need = "viewer") -> Library:
    """The library if the user has at least the role `need`; 404 if invisible, 403 if
    visible but not allowed (so ids of foreign libraries don't leak)."""
    library = Library.objects.filter(pk=library_id).select_related("owner").first()
    role = role_in(library, user) if library else None
    if library is None or role is None:
        raise HttpError(404, _("Library not found."))
    ranks = {"viewer": 0, Role.EDITOR.value: 1, "owner": 2}
    if ranks[role] < ranks[need]:
        raise HttpError(403, _("You are not allowed to do this in this library."))
    return library


def can_contribute(user: User) -> bool:
    """Admins, and whoever edits a library, may add games to the catalog (unreviewed)."""
    if is_admin(user):
        return True
    return (
        Library.objects.filter(owner=user).exists()
        or LibraryMember.objects.filter(user=user, role=Role.EDITOR).exists()
    )


def require_contributor(user: User) -> None:
    if not can_contribute(user):
        raise HttpError(403, _("Only editors of a library can add games."))
