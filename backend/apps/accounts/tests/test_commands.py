"""The user commands of core (ensure_admin, set_password) against our user model."""

import io
from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import User


@pytest.mark.django_db
def test_ensure_admin(monkeypatch: pytest.MonkeyPatch, settings: Any) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "")
    out = io.StringIO()
    call_command("ensure_admin", stdout=out)
    assert "skipping" in out.getvalue()

    monkeypatch.setenv("ADMIN_USERNAME", "root")
    monkeypatch.setenv("ADMIN_PASSWORD", "change-me")
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("ensure_admin", stdout=out)

    monkeypatch.setenv("ADMIN_PASSWORD", "a-real-password-42")
    call_command("ensure_admin", stdout=out)
    assert User.objects.get(username="root").is_superuser
    call_command("ensure_admin", stdout=out)
    assert "already exists" in out.getvalue()


@pytest.mark.django_db
def test_set_password(monkeypatch: pytest.MonkeyPatch, user: User) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("Sup3r-secret-pass\n"))
    call_command("set_password", "alice", "--stdin", stdout=io.StringIO())
    user.refresh_from_db()
    assert user.check_password("Sup3r-secret-pass")

    monkeypatch.setattr("sys.stdin", io.StringIO("123\n"))
    with pytest.raises(CommandError):
        call_command("set_password", "alice", "--stdin", stdout=io.StringIO())
    with pytest.raises(CommandError):
        call_command("set_password", "nobody", "--stdin")

    answers = iter(["One-pass-1234", "Other-pass-1234"])
    monkeypatch.setattr("getpass.getpass", lambda prompt: next(answers))
    with pytest.raises(CommandError):
        call_command("set_password", "alice")
    monkeypatch.setattr("getpass.getpass", lambda prompt: "Same-pass-1234")
    call_command("set_password", "alice", stdout=io.StringIO())
    user.refresh_from_db()
    assert user.check_password("Same-pass-1234")


@pytest.mark.django_db
def test_ensure_admin_ignores_the_case(monkeypatch: pytest.MonkeyPatch) -> None:
    User.objects.create_user("admin", "admin@example.com", "pw-admin-123")
    monkeypatch.setenv("ADMIN_USERNAME", "Admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "a-real-password-42")
    out = io.StringIO()
    call_command("ensure_admin", stdout=out)
    assert "already exists" in out.getvalue()
    assert User.objects.filter(username__iexact="admin").count() == 1


@pytest.mark.django_db
def test_set_password_ignores_the_case(monkeypatch: pytest.MonkeyPatch, user: User) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("Sup3r-secret-pass\n"))
    call_command("set_password", "ALICE", "--stdin", stdout=io.StringIO())
    user.refresh_from_db()
    assert user.check_password("Sup3r-secret-pass")
