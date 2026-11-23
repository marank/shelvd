"""How the pictures of terms and platforms read (`image_tone`, `photo_tone`): measured once
when a picture changes, sent to the pages, which keep the picture visible on either
background – a one-colour logo inverted, anything else outlined (see the frontend's
ToneBox)."""

from __future__ import annotations

from typing import Any

from django.db.models import Model

from apps.core.services.images import image_tone

# Picture field → its tone field.
TONED = {"image": "image_tone", "photo": "photo_tone"}


def measure(field: Any) -> str:
    if not field:
        return ""
    try:
        with field.open("rb") as file:
            return image_tone(file.read())
    except OSError:
        return ""  # the file is gone


def note_tones[T: Model](obj: T) -> T:
    """Measures each picture of a term or platform again and saves the tones that changed."""
    changed = []
    for picture, tone in TONED.items():
        if hasattr(obj, tone) and getattr(obj, tone) != (new := measure(getattr(obj, picture))):
            setattr(obj, tone, new)
            changed.append(tone)
    if changed:
        obj.save(update_fields=changed)
    return obj
