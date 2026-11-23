"""Usernames in any case: sign-in, the backend's edge cases and the API's guard."""

from typing import Any

import pytest
from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from django.test import Client, RequestFactory
from django.utils import translation

from apps.accounts.api.auth import current_user
from apps.accounts.backends import CaseInsensitiveModelBackend
from apps.accounts.models import User
from apps.accounts.services import RegistrationError, register_user


def test_login_with_the_username_in_another_case(user: User) -> None:
    client = Client()
    response = client.post(
        "/api/auth/login",
        {"username": "ALICE", "password": "pw-alice-123"},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["username"] == "alice"
    assert client.get("/api/auth/me").json()["id"] == str(user.pk)


def test_authenticate_edge_cases(user: User) -> None:
    assert authenticate(username="Alice", password="pw-alice-123") == user
    assert authenticate(username="Alice", password="wrong") is None
    assert authenticate(username="nobody", password="pw-alice-123") is None
    backend = CaseInsensitiveModelBackend()
    assert backend.authenticate(None, username="alice") is None
    assert backend.authenticate(None, password="pw-alice-123") is None
    user.is_active = False
    user.save()
    assert authenticate(username="alice", password="pw-alice-123") is None


def test_usernames_are_unique_regardless_of_case(db: None) -> None:
    User.objects.create_user("Bob", password="pw-upper-123")
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user("bob", password="pw-lower-123")
    assert authenticate(username="BOB", password="pw-upper-123") is not None


def test_register_user_service(db: None) -> None:
    carol = register_user("  carol ", " carol@example.com ", "a-long-password-1")
    assert (carol.username, carol.email) == ("carol", "carol@example.com")
    assert carol.check_password("a-long-password-1")
    with translation.override("en"):
        with pytest.raises(RegistrationError, match="not available"):
            register_user("CAROL", "", "a-long-password-1")
        with pytest.raises(RegistrationError, match="not available"):
            register_user("  ", "", "a-long-password-1")
    with pytest.raises(RegistrationError):
        register_user("dave", "", "123")
    assert not User.objects.filter(username="dave").exists()


def test_current_user_refuses_anonymous(rf: RequestFactory, db: None) -> None:
    from django.contrib.auth.models import AnonymousUser
    from ninja.errors import HttpError

    request: Any = rf.get("/")
    request.user = AnonymousUser()
    with pytest.raises(HttpError) as raised:
        current_user(request)
    assert raised.value.status_code == 401
