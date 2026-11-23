from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CatalogConfig(AppConfig):
    """Shared reference data: what exists (works, releases, platforms), not who owns it."""

    name = "apps.catalog"
    label = "catalog"
    verbose_name = _("Catalog")
