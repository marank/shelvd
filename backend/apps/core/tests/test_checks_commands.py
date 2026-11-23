from typing import Any

from django.apps import apps
from django.db import models

from apps.core.checks import uuid_primary_keys


def test_uuid_check_passes_for_project() -> None:
    assert uuid_primary_keys() == []


def test_uuid_check_flags_integer_pk() -> None:
    class IntPk(models.Model):  # noqa: DJ008
        class Meta:
            app_label = "core"

    try:
        errors = uuid_primary_keys([apps.get_app_config("core")])
        assert [e.id for e in errors] == ["core.E001"]
    finally:
        del apps.all_models["core"]["intpk"]
        apps.clear_cache()


def test_runserver_listens_on_backend_port(settings: Any) -> None:
    from django.core.management import get_commands

    from apps.core.management.commands.runserver import Command as Runserver

    assert get_commands()["runserver"] == "apps.core"
    assert Runserver.default_port == str(settings.BACKEND_PORT)
