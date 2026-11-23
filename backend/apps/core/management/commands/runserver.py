"""`runserver` that listens on BACKEND_PORT by default (native development).

Vite's proxy reads the same variable, so both agree without passing a port. apps.core
comes before django.contrib.staticfiles in INSTALLED_APPS, so this command wins; it
keeps the static file handling by subclassing that app's command.
"""

from django.conf import settings
from django.contrib.staticfiles.management.commands.runserver import (
    Command as StaticfilesRunserver,
)


class Command(StaticfilesRunserver):
    default_port = str(settings.BACKEND_PORT)
