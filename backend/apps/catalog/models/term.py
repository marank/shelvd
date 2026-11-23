from __future__ import annotations

import secrets

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import UUIDModel

from .choices import ImageTone


def term_image_upload_to(instance: CatalogTerm, filename: str) -> str:
    """A new name per upload (nginx caches /media/ for days)."""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    return f"terms/{instance._meta.model_name}/{instance.pk}-{secrets.token_hex(4)}.{extension}"


class CatalogTerm(UUIDModel):
    """What companies, genres and series share besides their name: a description per
    language ({"de": …, "en": …}, shown in the reader's language or else another one)
    and a picture (a logo, key art …) for their pages."""

    descriptions = models.JSONField(_("descriptions"), default=dict, blank=True)
    # SVG (checked for scripts and links) or JPEG/PNG/WebP.
    image = models.FileField(upload_to=term_image_upload_to, blank=True)
    # How the picture reads (services.tones), so pages keep it visible; "" = as it is.
    image_tone = models.CharField(max_length=5, choices=ImageTone.choices, blank=True)

    class Meta:
        abstract = True
