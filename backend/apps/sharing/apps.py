from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SharingConfig(AppConfig):
    """Personal lists (wishlists, favourites, …) and public read-only links."""

    name = "apps.sharing"
    label = "sharing"
    verbose_name = _("Sharing")
