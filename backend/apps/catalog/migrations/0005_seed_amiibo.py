"""Platform for amiibo figures (media type "toy")."""

from typing import Any

from django.db import migrations


def seed(apps: Any, schema_editor: Any) -> None:
    Platform = apps.get_model("catalog", "Platform")
    Platform.objects.get_or_create(
        slug="amiibo",
        defaults={
            "name": "amiibo",
            "short_name": "amiibo",
            "manufacturer": "Nintendo",
            "media_type": "toy",
            "release_year": 2014,
        },
    )


class Migration(migrations.Migration):
    dependencies = [('catalog', '0004_release_age_rating_release_product_code_and_more'),]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
