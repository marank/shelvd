"""Add-ons: optional Django apps in backend/addons/<name>/ (see addons/__init__.py)."""

from __future__ import annotations

import pkgutil
from collections.abc import Iterable
from importlib import import_module
from pathlib import Path
from typing import Protocol

from ninja import NinjaAPI, Router


class _AppConfig(Protocol):
    name: str


def installed(folder: Path) -> list[str]:
    """The add-on packages found in `folder`, as INSTALLED_APPS entries."""
    return [
        f"addons.{module.name}" for module in pkgutil.iter_modules([str(folder)]) if module.ispkg
    ]


def mount(api: NinjaAPI, app_configs: Iterable[_AppConfig]) -> None:
    """Adds every app's `api_routers` – `(prefix, "module:router")` pairs – to the API."""
    for app_config in app_configs:
        for prefix, target in getattr(app_config, "api_routers", ()):
            module, _, name = target.partition(":")
            router = getattr(import_module(module), name)
            if not isinstance(router, Router):
                raise TypeError(f"{target} is not a ninja Router")
            api.add_router(prefix, router)
