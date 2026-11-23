"""Logos stored on a plain black background (a JPEG with white lettering on black): that
background made transparent like a white one, and the logo's tone measured again."""

from typing import Any

from django.core.files.base import ContentFile
from django.db import migrations

from apps.core.services.images import clear_background, image_tone


def clear(apps: Any, schema_editor: Any) -> None:
    for name in ("Company", "Genre", "Series", "Franchise", "Platform"):
        for obj in apps.get_model("catalog", name).objects.exclude(image="").iterator():
            try:
                with obj.image.open("rb") as file:
                    data = file.read()
            except OSError:
                continue  # the file is gone
            cleared = clear_background(data, dark=True)
            if cleared is data:
                continue
            old = obj.image.name
            obj.image.save("picture.png", ContentFile(cleared), save=False)
            obj.image.storage.delete(old)
            obj.image_tone = image_tone(cleared)
            obj.save(update_fields=["image", "image_tone"])


class Migration(migrations.Migration):
    dependencies = [("catalog", "0026_image_tones")]

    operations = [migrations.RunPython(clear, migrations.RunPython.noop)]
