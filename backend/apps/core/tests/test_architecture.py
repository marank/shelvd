"""The import-linter contracts in pyproject.toml must cover every app.

`lint-imports` only checks the apps listed there; this test fails as soon as an app exists
that is missing, so a new app can't slip past the layer rules.
"""

import tomllib
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]


def contracts() -> dict[str, dict[str, list[str]]]:
    config = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
    return {contract["name"]: contract for contract in config["tool"]["importlinter"]["contracts"]}


def app_modules() -> set[str]:
    return {f"apps.{path.parent.name}" for path in (BACKEND / "apps").glob("*/apps.py")}


def test_every_app_has_the_layer_contract() -> None:
    containers = set(contracts()["Layers inside each app"]["containers"])
    assert app_modules() - containers == set()


def test_core_is_forbidden_to_import_every_other_app() -> None:
    forbidden = set(contracts()["core depends on no other app"]["forbidden_modules"])
    assert app_modules() - {"apps.core"} - forbidden == set()
