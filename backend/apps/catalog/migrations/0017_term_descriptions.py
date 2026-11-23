"""One description per language: the old single text goes under its language – Wikipedia
texts carry their source line ("Quelle: …" is German, "Source: …" English), anything else
counts as the site's default language."""

from typing import Any

from django.conf import settings
from django.db import migrations, models


def _language(text: str) -> str:
    if text.rstrip().endswith("Quelle: Wikipedia, CC BY-SA 4.0"):
        return "de"
    if text.rstrip().endswith("Source: Wikipedia, CC BY-SA 4.0"):
        return "en"
    return str(settings.LANGUAGE_CODE).split("-")[0]


def forwards(apps: Any, schema_editor: Any) -> None:
    for name in ("Company", "Genre", "Series"):
        model = apps.get_model("catalog", name)
        for term in model.objects.exclude(description=""):
            term.descriptions = {_language(term.description): term.description}
            term.save(update_fields=["descriptions"])


def backwards(apps: Any, schema_editor: Any) -> None:
    for name in ("Company", "Genre", "Series"):
        model = apps.get_model("catalog", name)
        for term in model.objects.exclude(descriptions={}):
            texts = term.descriptions
            term.description = texts.get(settings.LANGUAGE_CODE) or next(iter(texts.values()))
            term.save(update_fields=["description"])


class Migration(migrations.Migration):
    dependencies = [("catalog", "0016_company_details")]

    operations = [
        *(
            migrations.AddField(
                model_name=name,
                name="descriptions",
                field=models.JSONField(blank=True, default=dict, verbose_name="descriptions"),
            )
            for name in ("company", "genre", "series")
        ),
        migrations.RunPython(forwards, backwards),
        *(
            migrations.RemoveField(model_name=name, name="description")
            for name in ("company", "genre", "series")
        ),
    ]
