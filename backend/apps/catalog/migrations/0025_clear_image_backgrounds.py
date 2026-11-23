"""Pictures stored before backgrounds were cleared: a raster logo or photo on plain white
gets that background made transparent (a new PNG file; the old one is removed)."""

from typing import Any

from django.core.files.base import ContentFile
from django.db import migrations

from apps.core.services.images import clear_background

FIELDS = {
    "Company": ["image"],
    "Genre": ["image"],
    "Series": ["image"],
    "Franchise": ["image"],
    "Platform": ["image", "photo"],
}


def clear(apps: Any, schema_editor: Any) -> None:
    for model_name, fields in FIELDS.items():
        model = apps.get_model("catalog", model_name)
        for obj in model.objects.all().iterator():
            for name in fields:
                field = getattr(obj, name)
                if not field:
                    continue
                try:
                    with field.open("rb") as file:
                        data = file.read()
                except OSError:
                    continue  # the file is gone
                cleared = clear_background(data)
                if cleared is data:
                    continue
                old = field.name
                field.save("picture.png", ContentFile(cleared), save=False)
                field.storage.delete(old)
                obj.save(update_fields=[name])


class Migration(migrations.Migration):
    dependencies = [("catalog", "0024_series_franchise")]

    operations = [migrations.RunPython(clear, migrations.RunPython.noop)]
