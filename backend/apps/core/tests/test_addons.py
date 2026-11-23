"""The add-on seams in config: discovery and API routers."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from ninja import NinjaAPI, Router

from config.addons import installed, mount

router = Router()
not_a_router = object()


@router.get("ping")
def ping(request: object) -> str:
    return "pong"


def test_installed_lists_packages_only(tmp_path: Path) -> None:
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "__init__.py").write_text("")
    (tmp_path / "stray.py").write_text("")
    (tmp_path / "notes").mkdir()  # no __init__.py: not a package
    assert installed(tmp_path) == ["addons.demo"]


def test_installed_without_folder(tmp_path: Path) -> None:
    assert installed(tmp_path / "missing") == []


def test_mount_adds_routers() -> None:
    api = NinjaAPI(urls_namespace="addons-test")
    with_routers = SimpleNamespace(
        name="addons.demo", api_routers=[("/demo", f"{__name__}:router")]
    )
    mount(api, [SimpleNamespace(name="apps.plain"), with_routers])
    assert any(prefix == "/demo" for prefix, _ in api._routers)


def test_mount_refuses_other_objects() -> None:
    api = NinjaAPI(urls_namespace="addons-test-2")
    broken = SimpleNamespace(name="addons.bad", api_routers=[("/bad", f"{__name__}:not_a_router")])
    with pytest.raises(TypeError):
        mount(api, [broken])
