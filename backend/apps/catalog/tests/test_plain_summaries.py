import importlib

from django.apps import apps

from apps.catalog.models import Work

migration = importlib.import_module("apps.catalog.migrations.0018_plain_summaries")


def test_html_summaries_become_plain_text(db: None) -> None:
    dirty = Work.objects.create(
        title="A", summary="<b>Rally!</b>\n\nModes:<ul><li>Story</li><li>Versus</li></ul>"
    )
    clean = Work.objects.create(title="B", summary="Plain & simple, 1 < 2.")
    migration.clean(apps, None)
    dirty.refresh_from_db()
    clean.refresh_from_db()
    assert dirty.summary == "Rally!\n\nModes:\n\n• Story\n• Versus"
    assert clean.summary == "Plain & simple, 1 < 2."
