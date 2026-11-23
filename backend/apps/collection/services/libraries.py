import secrets

from django.db import IntegrityError, transaction
from django.utils.translation import gettext as _
from ninja.errors import HttpError

from apps.accounts.models import User
from apps.core.services.files import delete_files_on_commit

from ..models import Item, Library, LibraryMember, Overview, Role


@transaction.atomic
def create_library(owner: User, name: str, description: str = "") -> Library:
    name = name.strip()
    if not name:
        raise HttpError(400, _("A name is required."))
    library = Library.objects.create(owner=owner, name=name, description=description)
    # A useful start: the classic "by platform" view.
    Overview.objects.create(
        library=library, user=owner, name=_("By platform"), group_by=["platform.name"]
    )
    return library


@transaction.atomic
def delete_library(library: Library) -> None:
    """The library with everything in it, and the cover files of its copies (removed once
    the deletion is committed)."""
    copies = Item.objects.filter(library=library).exclude(cover_override="").order_by("pk")
    delete_files_on_commit(item.cover_override for item in copies)
    library.delete()


def enable_public_link(library: Library) -> Library:
    if not library.public_token:
        library.public_token = secrets.token_urlsafe(24)
        library.save(update_fields=["public_token", "updated_at"])
    return library


def disable_public_link(library: Library) -> Library:
    library.public_token = None
    library.save(update_fields=["public_token", "updated_at"])
    return library


def add_member(library: Library, username: str, role: Role) -> LibraryMember:
    user = User.objects.filter(username__iexact=username.strip()).order_by("date_joined").first()
    if user is None:
        raise HttpError(404, _("No user with this name."))
    if user.pk == library.owner_id:
        raise HttpError(400, _("The owner is already part of the library."))
    try:
        with transaction.atomic():
            return LibraryMember.objects.create(library=library, user=user, role=role)
    except IntegrityError as exc:
        raise HttpError(409, _("This user is already a member.")) from exc
