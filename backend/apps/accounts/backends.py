"""Sign-in with the username in any case: "Alice" and "alice" are the same account."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.backends import ModelBackend
from django.http import HttpRequest

from .models import User


class CaseInsensitiveModelBackend(ModelBackend):
    """Django's ModelBackend, looking the username up with `iexact`.

    Usernames are unique regardless of case (constraint `unique_username_ci`), so the
    lookup finds at most one account.
    """

    def authenticate(
        self,
        request: HttpRequest | None,
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> User | None:
        if username is None or password is None:
            return None
        user = find_user(username)
        if user is None:
            # Hash anyway, so an unknown username takes as long as a wrong password.
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None


def find_user(username: str) -> User | None:
    """The account with this username in any case (unique regardless of case)."""
    return User.objects.filter(username__iexact=username).first()
