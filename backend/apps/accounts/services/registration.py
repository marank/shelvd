"""Self-service sign-up: who may get an account and with which password."""

from __future__ import annotations

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from ..models import User


class RegistrationError(Exception):
    """The account can't be created; `message` says why, in the request's language."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@transaction.atomic
def register_user(username: str, email: str, password: str) -> User:
    """Create a plain user. The username is free only if no one has it in any case."""
    username = username.strip()
    if not username or User.objects.filter(username__iexact=username).exists():
        raise RegistrationError(_("This username is not available."))
    user = User(username=username, email=email.strip())
    try:
        password_validation.validate_password(password, user)
    except ValidationError as exc:
        raise RegistrationError(" ".join(exc.messages)) from exc
    user.set_password(password)
    user.save()
    return user
