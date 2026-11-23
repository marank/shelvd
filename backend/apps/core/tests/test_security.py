"""No side effects beyond our own responses: behind a TLS proxy the app neither redirects
to https nor sends HSTS – both are the proxy's job."""

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from django.test import Client, override_settings

SETTINGS = Path(__file__).resolve().parents[3] / "config" / "settings.py"


def production_settings(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """config/settings.py evaluated as in production behind a TLS proxy."""
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("APP_URLS", "https://app.example.com")
    monkeypatch.setenv("SECRET_KEY", "test-only-not-secret-but-long-and-random-enough-0123456789")
    spec = importlib.util.spec_from_file_location("config.production_probe", SETTINGS)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def production(monkeypatch: pytest.MonkeyPatch) -> Any:
    module = production_settings(monkeypatch)
    security = {name: value for name, value in vars(module).items() if name.startswith("SECURE_")}
    with override_settings(
        DEBUG=False,
        ALLOWED_HOSTS=module.ALLOWED_HOSTS,
        SESSION_COOKIE_SECURE=module.SESSION_COOKIE_SECURE,
        CSRF_COOKIE_SECURE=module.CSRF_COOKIE_SECURE,
        **security,
    ):
        yield module


def test_settings_leave_redirect_and_hsts_to_the_proxy(production: Any) -> None:
    assert production.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert production.SESSION_COOKIE_SECURE is True
    assert production.CSRF_COOKIE_SECURE is True
    assert not getattr(production, "SECURE_SSL_REDIRECT", False)
    assert not getattr(production, "SECURE_HSTS_SECONDS", 0)
    assert set(production.SILENCED_SYSTEM_CHECKS) == {"security.W004", "security.W008"}


@pytest.mark.django_db
def test_https_through_the_proxy_gets_no_hsts(production: Any) -> None:
    response = Client().get(
        "/api/health", HTTP_HOST="app.example.com", headers={"X-Forwarded-Proto": "https"}
    )
    assert response.status_code == 200
    assert "Strict-Transport-Security" not in response.headers


@pytest.mark.django_db
def test_plain_http_is_answered_not_redirected(production: Any) -> None:
    for path in ("/api/health", "/api/auth/me"):
        response = Client().get(path, HTTP_HOST="app.example.com")
        assert response.status_code in {200, 401}, path
        assert "Location" not in response.headers
        assert "Strict-Transport-Security" not in response.headers
