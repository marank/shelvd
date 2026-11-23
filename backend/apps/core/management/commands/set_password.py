"""Set a user's password: `python manage.py set_password <username>` (prompts twice)."""

import getpass
import sys
from argparse import ArgumentParser
from typing import Any

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Set the password of an existing user."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("username")
        parser.add_argument(
            "--stdin", action="store_true", help="Read the password from stdin (for scripts)."
        )

    def handle(self, *args: Any, username: str, stdin: bool, **options: Any) -> None:
        User = get_user_model()
        # Usernames are case-insensitive (apps.accounts.backends).
        user = (
            User.objects.filter(**{f"{User.USERNAME_FIELD}__iexact": username})
            .order_by("date_joined")
            .first()
        )
        if user is None:
            raise CommandError(f"User {username!r} does not exist.")

        if stdin:
            password = sys.stdin.readline().rstrip("\n")
        else:
            password = getpass.getpass("New password: ")
            if password != getpass.getpass("Repeat password: "):
                raise CommandError("Passwords do not match.")

        try:
            password_validation.validate_password(password, user)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc

        user.set_password(password)
        user.save(update_fields=["password"])
        self.stdout.write(self.style.SUCCESS(f"Password for {username!r} updated."))
