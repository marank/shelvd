from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TrackingConfig(AppConfig):
    """Games a person watches, pre-orders or bought but doesn't have on the shelf yet."""

    name = "apps.tracking"
    label = "tracking"
    verbose_name = _("Tracking")
