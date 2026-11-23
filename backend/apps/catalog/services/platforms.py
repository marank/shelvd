"""Creating, changing and deleting platforms; their colour, icon, picture, descriptions and
facts (generation, end of production, predecessors)."""

from __future__ import annotations

import re
from typing import Any, Literal

from django.db import IntegrityError, transaction
from django.utils.text import slugify
from django.utils.translation import gettext as _
from ninja import UploadedFile
from ninja.errors import HttpError

from apps.core.services.images import is_dark_mark, store_icon

from ..models import Platform, PlatformIcon
from ..schemas import PlatformIn, PlatformPatch
from .terms import merge_descriptions
from .tones import note_tones

COLOR = re.compile(r"#[0-9a-fA-F]{6}")


def _unique_slug(name: str) -> str:
    base = slugify(name)[:45] or "platform"
    slug, n = base, 2
    while Platform.objects.filter(slug=slug).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


def _validate(fields: dict[str, Any]) -> None:
    """Refuse values the form can't send; normalises the name in place."""
    if "name" in fields:
        fields["name"] = (fields["name"] or "").strip()
        if not fields["name"]:
            raise HttpError(400, _("Enter a name."))
    color = fields.get("color")
    if color and not COLOR.fullmatch(color):
        raise HttpError(400, _("Choose a colour like #e60012."))
    icon = fields.get("icon")
    if icon and icon not in PlatformIcon.values:
        raise HttpError(400, _("Unknown icon."))
    generation = fields.get("generation")
    if generation is not None and not 1 <= generation <= 20:
        raise HttpError(400, _("Enter a console generation from 1 to 20."))
    discontinued = fields.get("discontinued")
    if discontinued is not None and not 1950 <= discontinued <= 2100:
        raise HttpError(400, _("Enter a year with four digits."))


def _set_predecessors(platform: Platform, predecessors: list[Any]) -> None:
    others = Platform.objects.filter(pk__in=predecessors).exclude(pk=platform.pk)
    if others.count() != len(set(predecessors) - {platform.pk}):
        raise HttpError(400, _("Unknown platform."))
    platform.predecessors.set(others)


def _apply(platform: Platform, fields: dict[str, Any]) -> None:
    _validate(fields)
    if "descriptions" in fields:
        fields["descriptions"] = merge_descriptions(platform.descriptions, fields["descriptions"])
    predecessors = fields.pop("predecessors", None)
    if "igdb_id" in fields:
        igdb_id = fields.pop("igdb_id")
        ids = {k: v for k, v in platform.external_ids.items() if k != "igdb"}
        platform.external_ids = {**ids, "igdb": igdb_id} if igdb_id is not None else ids
    for name, value in fields.items():
        setattr(platform, name, value.strip() if isinstance(value, str) else value)
    try:
        with transaction.atomic():
            platform.save()
    except IntegrityError as exc:
        raise HttpError(409, _("A platform with this name already exists.")) from exc
    if predecessors is not None:
        _set_predecessors(platform, predecessors)


def create_platform(data: PlatformIn) -> Platform:
    platform = Platform(slug=_unique_slug(data.name))
    _apply(platform, data.model_dump())
    return platform


def update_platform(platform: Platform, data: PlatformPatch) -> Platform:
    fields = data.model_dump(exclude_unset=True)
    # None means "leave it" for the required texts, "clear it" for the optional ones.
    for name in ("name", "short_name", "manufacturer", "media_type", "color", "icon"):
        if fields.get(name, "") is None:
            fields.pop(name)
    _apply(platform, fields)
    return platform


def delete_platform(platform: Platform) -> None:
    if platform.releases.exists():
        raise HttpError(409, _("This platform is still in use and can't be deleted."))
    for field in (platform.icon_image, platform.image, platform.photo):
        if field:
            field.delete(save=False)
    platform.delete()


def set_icon(platform: Platform, upload: UploadedFile) -> Platform:
    store_icon(platform.icon_image, upload)
    return note_icon(platform)


def note_icon(platform: Platform) -> Platform:
    """Saves the icon and whether it's a dark mark (inverted on dark backgrounds)."""
    platform.icon_image.seek(0)
    platform.icon_dark = is_dark_mark(platform.icon_image.read())
    platform.save(update_fields=["icon_image", "icon_dark"])
    return platform


def remove_icon(platform: Platform) -> Platform:
    if platform.icon_image:
        platform.icon_image.delete(save=False)
    platform.icon_dark = False
    platform.save(update_fields=["icon_image", "icon_dark"])
    return platform


PICTURES: tuple[Literal["image", "photo"], ...] = ("image", "photo")  # logo, photo


def set_picture(platform: Platform, slot: str, upload: UploadedFile) -> Platform:
    """The page's logo (`image`) or photo (`photo`), up to 2 MB."""
    store_icon(getattr(platform, slot), upload, max_kb=2048, logo=slot == "image")
    platform.save(update_fields=[slot])
    return note_tones(platform)


def remove_picture(platform: Platform, slot: str) -> Platform:
    field = getattr(platform, slot)
    if field:
        field.delete(save=False)
    platform.save(update_fields=[slot])
    return note_tones(platform)
