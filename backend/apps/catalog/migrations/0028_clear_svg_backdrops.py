"""SVG logos that draw a plain black or white rectangle over the whole picture first: that
rectangle removed like a raster logo's background, and the logo's tone measured again."""

from typing import Any

from django.core.files.base import ContentFile
from django.db import migrations

from apps.core.services.images import clear_background, image_tone


def clear(apps: Any, schema_editor: Any) -> None:
    for name in ("Company", "Genre", "Series", "Franchise", "Platform"):
        for obj in apps.get_model("catalog", name).objects.exclude(image="").iterator():
            if not obj.image.name.endswith(".svg"):
                continue
            try:
                with obj.image.open("rb") as file:
                    data = file.read()
            except OSError:
                continue  # the file is gone
            cleared = clear_background(data, dark=True)
            if cleared is data:
                continue
            old = obj.image.name
            obj.image.save("picture.svg", ContentFile(cleared), save=False)
            obj.image.storage.delete(old)
            obj.image_tone = image_tone(cleared)
            obj.save(update_fields=["image", "image_tone"])


class Migration(migrations.Migration):
    dependencies = [("catalog", "0027_clear_dark_logo_backgrounds")]

    operations = [migrations.RunPython(clear, migrations.RunPython.noop)]
