from typing import Any

import pytest
from django.test import Client

from apps.accounts.models import User


@pytest.fixture
def csrf_client(db: None) -> Client:
    return Client(enforce_csrf_checks=True)


def _token(client: Client) -> str:
    response = client.get("/api/auth/csrf")
    assert response.status_code == 204
    return str(client.cookies["csrftoken"].value)


def test_health(anon_api: Any) -> None:
    assert anon_api.get("/health").json() == {"status": "ok"}


def test_login_requires_csrf(csrf_client: Client, user: User) -> None:
    response = csrf_client.post(
        "/api/auth/login",
        {"username": "alice", "password": "pw-alice-123"},
        content_type="application/json",
    )
    assert response.status_code == 403


def test_login_me_logout(csrf_client: Client, user: User) -> None:
    token = _token(csrf_client)
    assert csrf_client.get("/api/auth/me").status_code == 401
    bad = csrf_client.post(
        "/api/auth/login",
        {"username": "alice", "password": "wrong"},
        content_type="application/json",
        headers={"X-CSRFToken": token},
    )
    assert bad.status_code == 400
    good = csrf_client.post(
        "/api/auth/login",
        {"username": "alice", "password": "pw-alice-123"},
        content_type="application/json",
        headers={"X-CSRFToken": token},
    )
    assert good.status_code == 200
    assert good.json()["username"] == "alice"
    me = csrf_client.get("/api/auth/me").json()
    assert me["id"] == str(user.pk)
    # Django rotates the token on login; the new cookie is required from now on.
    token = str(csrf_client.cookies["csrftoken"].value)
    assert csrf_client.post("/api/auth/logout").status_code == 403
    out = csrf_client.post("/api/auth/logout", headers={"X-CSRFToken": token})
    assert out.status_code == 204
    assert csrf_client.get("/api/auth/me").status_code == 401


def test_register(anon_api: Any, settings: Any, user: User) -> None:
    payload = {"username": "carol", "password": "a-long-password-1"}
    assert anon_api.post("/auth/register", payload).status_code == 403
    settings.REGISTRATION_ENABLED = True
    assert (
        anon_api.post("/auth/register", {"username": "Alice", "password": "x" * 12}).status_code
        == 400
    )
    assert (
        anon_api.post("/auth/register", {"username": "dave", "password": "123"}).status_code == 400
    )
    response = anon_api.post("/auth/register", payload)
    assert response.status_code == 201
    assert anon_api.get("/auth/me").json()["username"] == "carol"


def test_register_requires_csrf(settings: Any, db: None) -> None:
    settings.REGISTRATION_ENABLED = True
    client = Client(enforce_csrf_checks=True)
    response = client.post(
        "/api/auth/register",
        {"username": "eve", "password": "a-long-password-1"},
        content_type="application/json",
    )
    assert response.status_code == 403
    assert str(User.objects.filter(username="eve").count()) == "0"
