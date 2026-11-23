from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import UUIDModel

from .choices import ImageTone, MediaType, PlatformIcon


def icon_upload_to(instance: Platform, filename: str) -> str:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    return f"platforms/{instance.id}.{extension}"


def photo_upload_to(instance: Platform, filename: str) -> str:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"platforms/{instance.id}-photo.{extension}"


def image_upload_to(instance: Platform, filename: str) -> str:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    return f"platforms/{instance.id}-picture.{extension}"


class Platform(UUIDModel):
    """A console, handheld or computer (later also DVD, Blu-ray, …): its badge (short name,
    colour, symbol or small logo) and its page (picture, descriptions by language, facts)."""

    name = models.CharField(max_length=100, unique=True)
    short_name = models.CharField(max_length=20, blank=True)
    slug = models.SlugField(max_length=50, unique=True)
    manufacturer = models.CharField(max_length=100, blank=True)
    media_type = models.CharField(max_length=10, choices=MediaType.choices, default=MediaType.GAME)
    release_year = models.PositiveSmallIntegerField(null=True, blank=True)
    # Provider ids, e.g. {"igdb": 20}; used to map provider records onto our platforms.
    external_ids = models.JSONField(default=dict, blank=True)
    # Shown on the platform badge; empty = the manufacturer's colour.
    color = models.CharField(max_length=7, blank=True)  # "#e60012"
    icon = models.CharField(max_length=20, choices=PlatformIcon.choices, blank=True)
    # An uploaded icon or small logo (SVG/PNG/WebP/JPEG) wins over the built-in symbol.
    icon_image = models.FileField(upload_to=icon_upload_to, blank=True)
    # A dark mark in one colour (a black glyph): shown inverted on dark backgrounds.
    icon_dark = models.BooleanField(default=False)
    # The page's pictures: its logo and a photo of the device.
    image = models.FileField(_("picture"), upload_to=image_upload_to, blank=True)
    photo = models.FileField(_("photo"), upload_to=photo_upload_to, blank=True)
    # How logo and photo read (services.tones); "" = as they are.
    image_tone = models.CharField(max_length=5, choices=ImageTone.choices, blank=True)
    photo_tone = models.CharField(max_length=5, choices=ImageTone.choices, blank=True)
    # {"de": "…", "en": "…"}: one text per language, like companies'.
    descriptions = models.JSONField(_("descriptions"), default=dict, blank=True)
    generation = models.PositiveSmallIntegerField(_("generation"), null=True, blank=True)
    discontinued = models.PositiveSmallIntegerField(_("discontinued"), null=True, blank=True)
    predecessors = models.ManyToManyField(
        "self", symmetrical=False, blank=True, related_name="successors"
    )

    class Meta:
        ordering = ["manufacturer", "release_year", "name"]
        verbose_name = _("platform")
        verbose_name_plural = _("platforms")

    def __str__(self) -> str:
        return self.name
