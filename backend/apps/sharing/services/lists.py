import secrets

from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils.translation import gettext as _
from ninja.errors import HttpError

from apps.accounts.models import User
from apps.catalog.models import Release
from apps.collection.models import Item
from apps.collection.services.access import visible_libraries

from ..models import CustomList, ListEntry
from ..schemas import EntryIn


def add_entry(custom_list: CustomList, data: EntryIn, user: User) -> ListEntry:
    release = Release.objects.filter(pk=data.release_id).first()
    if release is None:
        raise HttpError(400, _("Unknown release."))
    item = None
    if data.item_id:
        # Only copies the user can see (own or shared libraries).
        item = Item.objects.filter(
            pk=data.item_id, release=release, library__in=visible_libraries(user)
        ).first()
        if item is None:
            raise HttpError(400, _("Unknown item."))
    position = (custom_list.entries.aggregate(m=Max("position"))["m"] or 0) + 1
    try:
        with transaction.atomic():
            return ListEntry.objects.create(
                custom_list=custom_list,
                release=release,
                item=item,
                note=data.note,
                position=position,
            )
    except IntegrityError as exc:
        raise HttpError(409, _("This game is already on the list.")) from exc


def toggle_public(custom_list: CustomList, enabled: bool) -> CustomList:
    custom_list.public_token = (
        (custom_list.public_token or secrets.token_urlsafe(24)) if enabled else None
    )
    custom_list.save(update_fields=["public_token", "updated_at"])
    return custom_list
