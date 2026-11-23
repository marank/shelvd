"""Create the first administrator from ADMIN_* env vars if that user does not exist yet.

Runs on every container start; it never touches an existing user, so changing
ADMIN_PASSWORD later has no effect (use `manage.py set_password <username>`).
"""

import os
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from config.env import INSECURE_SECRET_VALUES


class Command(BaseCommand):
    help = "Create the initial superuser from ADMIN_USERNAME / ADMIN_EMAIL / ADMIN_PASSWORD."

    def handle(self, *args: Any, **options: Any) -> None:
        username = os.environ.get("ADMIN_USERNAME", "").strip()
        if not username:
            self.stdout.write("ADMIN_USERNAME not set, skipping admin creation.")
            return

        User = get_user_model()
        # Usernames are case-insensitive (apps.accounts.backends): "Admin" is "admin".
        if User.objects.filter(**{f"{User.USERNAME_FIELD}__iexact": username}).exists():
            self.stdout.write(f"Admin user {username!r} already exists.")
            return

        password = os.environ.get("ADMIN_PASSWORD", "")
        if password in INSECURE_SECRET_VALUES and not settings.DEBUG:
            raise CommandError("Set ADMIN_PASSWORD to a real password before the first start.")

        User.objects.create_superuser(
            **{User.USERNAME_FIELD: username},
            email=os.environ.get("ADMIN_EMAIL", ""),
            password=password,
        )
        self.stdout.write(self.style.SUCCESS(f"Created admin user {username!r}."))
