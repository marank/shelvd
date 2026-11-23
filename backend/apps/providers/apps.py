from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProvidersConfig(AppConfig):
    """External sources (IGDB, TheGamesDB, …) behind one interface."""

    name = "apps.providers"
    label = "providers"
    verbose_name = _("Providers")
