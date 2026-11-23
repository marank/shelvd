# ruff: noqa: E501
from typing import Any

import httpx
import pytest
from django.test import override_settings

from apps.accounts.models import User
from apps.providers.models import Integration
from apps.providers.services.integrations import config, decrypt, encrypt, mask, save
from apps.providers.services.scheduler import run_due

from .fakes import response, router


@pytest.fixture
def admin_api(api: Any, user: User) -> Any:
    user.is_staff = True
    user.save()
    return api


def test_config_defaults_secrets_and_masking(db: None) -> None:
    cfg = config("hltb")
    assert (cfg.enabled, cfg.options["max_age_hours"], cfg.active) == (False, 720, False)
    cfg = save(
        "opencritic",
        enabled=True,
        options={"max_age_hours": "48"},
        secrets={"rapidapi_key": " k-12345678 "},
    )
    assert (cfg.active, cfg.options["max_age_hours"], cfg.secrets) == (
        True,
        48,
        {"rapidapi_key": "k-12345678"},
    )
    row = Integration.objects.get(key="opencritic")
    assert "k-12345678" not in row.secrets  # stored encrypted
    assert mask("k-12345678") == "••••5678"
    assert mask("short") == "••••"
    # Only the secrets sent change; "" removes one.
    assert save("opencritic", secrets={}).secrets == {"rapidapi_key": "k-12345678"}
    assert save("opencritic", secrets={"rapidapi_key": ""}).active is False
    assert decrypt(encrypt("x")) == "x"
    assert decrypt("garbage") is None
    with override_settings(SECRET_KEY="another"):  # new SECRET_KEY: secrets are unreadable
        save("igdb", secrets={"client_id": "a"})
    assert config("igdb").secrets == {}


@pytest.mark.parametrize(
    "payload",
    [{"options": {"nope": 1}}, {"options": {"rapidapi_key": "x"}}, {"secrets": {"max_age_hours": "1"}},
     {"options": {"max_age_hours": "soon"}}, {"options": {"max_age_hours": -1}}],
)  # fmt: skip
def test_invalid_settings(admin_api: Any, payload: dict[str, Any]) -> None:
    assert admin_api.patch("/integrations/opencritic", payload).status_code == 400


def test_admin_api(admin_api: Any, other_api: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    assert other_api.get("/integrations").status_code == 403
    assert other_api.patch("/integrations/igdb", {"enabled": True}).status_code == 403
    listed = admin_api.get("/integrations").json()
    # Built-in ones first; add-ons (backend/addons) may add more after them.
    assert [i["key"] for i in listed][:6] == [
        "igdb", "wikipedia", "hltb", "opencritic", "thegamesdb", "screenscraper",
    ]  # fmt: skip
    hltb = next(i for i in listed if i["key"] == "hltb")
    assert hltb["unofficial"]
    assert hltb["refreshes"]
    saved = admin_api.patch(
        "/integrations/thegamesdb",
        {"enabled": True, "secrets": {"api_key": "abcdefghijkl"}},
    ).json()
    assert saved["active"] is True
    field = saved["fields"][0]
    assert (field["secret"], field["has_value"], field["masked"]) == (True, True, "••••ijkl")
    assert "abcdefghijkl" not in str(saved)
    assert admin_api.patch("/integrations/nope", {"enabled": True}).status_code == 404

    # Testing: missing fields, failure (error is remembered), success.
    assert admin_api.post("/integrations/opencritic/test").json()["ok"] is False
    monkeypatch.setattr("httpx.get", router({}))
    failed = admin_api.post("/integrations/thegamesdb/test").json()
    assert failed["ok"] is False
    assert "TheGamesDB" in failed["message"]
    assert "TheGamesDB" in config("thegamesdb").row.last_error  # type: ignore[union-attr]
    monkeypatch.setattr(
        "httpx.get",
        router(
            {
                "https://api.thegamesdb.net": lambda *a, **k: response(
                    json={"remaining_monthly_allowance": 997}
                )
            }
        ),
    )
    assert admin_api.post("/integrations/thegamesdb/test").json() == {
        "ok": True,
        "message": "OK – noch 997 Abfragen in diesem Monat",
    }
    assert config("thegamesdb").row.last_ok_at is not None  # type: ignore[union-attr]
    assert admin_api.post("/integrations/nope/test").status_code == 404


def test_scheduler_runs_due_jobs(db: None, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def batch(key: str, limit: int) -> int:
        calls.append(key)
        return 3

    monkeypatch.setattr("apps.providers.services.facts.refresh_batch", batch)
    assert run_due() == {}  # nothing switched on
    save("hltb", enabled=True, options={"periodic": True, "periodic_hours": 24, "batch": 5})
    assert run_due() == {"hltb": 3}
    assert run_due() == {}  # not due again yet
    assert calls == ["hltb"]


def test_scheduler_command(db: None, monkeypatch: pytest.MonkeyPatch) -> None:
    from io import StringIO

    from django.core.management import call_command

    monkeypatch.setattr(
        "apps.providers.management.commands.run_scheduler.run_due", lambda: {"hltb": 2}
    )
    out = StringIO()
    call_command("run_scheduler", "--once", stdout=out)
    assert "hltb: 2 games refreshed" in out.getvalue()


def test_scheduler_survives_database_errors(db: None, monkeypatch: pytest.MonkeyPatch) -> None:
    from io import StringIO

    from django.core.management import call_command
    from django.db import DatabaseError

    def broken() -> dict[str, int]:
        raise DatabaseError("no such table")

    monkeypatch.setattr("apps.providers.management.commands.run_scheduler.run_due", broken)
    err = StringIO()
    call_command("run_scheduler", "--once", stderr=err)
    assert "database not ready" in err.getvalue()


def test_failing_source_keeps_running(db: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("httpx.get", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("x")))
    save("thegamesdb", enabled=True)
    from apps.providers.sources import ProviderError
    from apps.providers.sources.thegamesdb import TheGamesDBSource

    with pytest.raises(ProviderError):
        TheGamesDBSource().test()
