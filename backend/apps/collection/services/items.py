from typing import Any

from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile
from django.db import transaction
from django.utils.translation import gettext as _
from ninja.errors import HttpError

from apps.catalog.models import DatePrecision, Release
from apps.catalog.models.dates import period
from apps.core.services.files import delete_files_on_commit
from apps.core.services.images import store_image
from apps.providers.services import covers

from ..models import Item, Library, Location, Person, Tag
from ..schemas import ItemIn, ItemPatch


def _resolve_refs(library: Library, data: dict[str, Any]) -> dict[str, Any]:
    """Replace *_id fields by objects, making sure they belong to this library."""
    values = dict(data)
    if "release_id" in values:
        release = Release.objects.filter(pk=values.pop("release_id")).first()
        if release is None:
            raise HttpError(400, _("Unknown release."))
        values["release"] = release
    if "location_id" in values:
        values["location"] = _in_library(
            Location, values.pop("location_id"), library, _("Unknown location.")
        )
    if "owner_id" in values:
        values["owner"] = _in_library(Person, values.pop("owner_id"), library, _("Unknown person."))
    for choice in ("condition", "completeness", "play_status"):
        if choice in values and values[choice] is None:
            values[choice] = ""
    return values


def _in_library[M: (Location, Person)](
    model: type[M], pk: Any, library: Library, unknown: str
) -> M | None:
    """The library's location or person with this id; None for no id."""
    if not pk:
        return None
    found = model.objects.filter(pk=pk, library=library).first()
    if found is None:
        raise HttpError(400, unknown)
    return found


def set_item_cover(item: Item, upload: UploadedFile[bytes] | None, max_mb: int) -> Item:
    """Own cover for this copy; None removes it (the catalog cover shows again)."""
    if upload is None:
        item.cover_override.delete(save=False)
    else:
        store_image(item.cover_override, upload, max_mb)
    # The dimensions too: they give the cover's aspect ratio.
    item.save(
        update_fields=[
            "cover_override",
            "cover_override_width",
            "cover_override_height",
            "updated_at",
        ]
    )
    return item


def set_item_cover_from(item: Item, token: str, max_mb: int) -> Item:
    """Own cover for this copy from a covers source candidate (see providers.covers)."""
    content, content_type = covers.fetch(token)
    extension = covers.IMAGE_TYPES[content_type]
    upload = SimpleUploadedFile(f"cover.{extension}", content, content_type=content_type)
    return set_item_cover(item, upload, max_mb)


def reset_overrides(item: Item) -> Item:
    """Everything as the release again: title, cover, edition, region and date."""
    if item.cover_override:
        set_item_cover(item, None, 0)
    item.title_override = item.edition_override = item.region_override = ""
    item.release_precision_override = ""
    item.release_date_override = item.release_date_end_override = None
    item.save()
    return item


def set_tags(item: Item, names: list[str]) -> None:
    """Replace the item's tags; unknown names become tags of its library."""
    clean = sorted({n.strip()[:100] for n in names if n.strip()})
    item.tags.set([Tag.objects.get_or_create(library_id=item.library_id, name=n)[0] for n in clean])


def create_item(library: Library, data: ItemIn) -> Item:
    values = _resolve_refs(library, data.model_dump(exclude={"tags"}))
    item = Item.objects.create(library=library, **values)
    set_tags(item, data.tags)
    return item


DATE_OVERRIDES = ("release_date_override", "release_date_end_override")
TEXT_OVERRIDES = ("title_override", "edition_override", "region_override")


def _date_override(values: dict[str, Any]) -> None:
    """A date of its own comes with its precision; it's normalized like a release's."""
    if "release_precision_override" not in values:
        for name in DATE_OVERRIDES:
            values.pop(name, None)
        return
    precision = values["release_precision_override"] or ""
    if not precision:
        values.update(release_precision_override="", **dict.fromkeys(DATE_OVERRIDES))
        return
    start, end = period(
        precision, values.get("release_date_override"), values.get("release_date_end_override")
    )
    values["release_date_override"] = start
    values["release_date_end_override"] = end if precision == DatePrecision.WINDOW else None


def update_item(item: Item, data: ItemPatch) -> Item:
    values = _resolve_refs(item.library, data.model_dump(exclude_unset=True, exclude={"tags"}))
    if values.get("release") is None:
        values.pop("release", None)
    for name in ("format", "status", "notes", *TEXT_OVERRIDES):
        if name in values and values[name] is None:
            values.pop(name)
    for name in ("title_override", "edition_override"):
        if name in values:
            values[name] = values[name].strip()
    if values.get("release_precision_override") is None:
        values.pop("release_precision_override", None)
    _date_override(values)
    for name, value in values.items():
        setattr(item, name, value)
    item.save()
    if data.tags is not None:
        set_tags(item, data.tags)
    return item


@transaction.atomic
def delete_item(item: Item) -> None:
    """The copy, its loans and its own cover file (removed once the deletion is committed)."""
    delete_files_on_commit([item.cover_override])
    item.delete()
