"""Every picture's tone measured again by the current rules: dark parts right on the
background (dark lettering beside a bright symbol) get a rim."""

from typing import Any

from django.db import migrations

from apps.core.services.images import image_tone

PICTURES = {"image": "image_tone", "photo": "photo_tone"}


def measure(apps: Any, schema_editor: Any) -> None:
    for name in ("Company", "Genre", "Series", "Franchise", "Platform"):
        for obj in apps.get_model("catalog", name).objects.all().iterator():
            changed = []
            for picture, tone in PICTURES.items():
                field = getattr(obj, picture, None)
                if not field:
                    continue
                try:
                    with field.open("rb") as file:
                        setattr(obj, tone, image_tone(file.read()))
                except OSError:
                    continue  # the file is gone
                changed.append(tone)
            if changed:
                obj.save(update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [("catalog", "0028_clear_svg_backdrops")]

    operations = [migrations.RunPython(measure, migrations.RunPython.noop)]
