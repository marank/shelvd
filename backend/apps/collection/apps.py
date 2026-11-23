from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CollectionConfig(AppConfig):
    """Libraries and what is in them: copies, places, people, loans, saved overviews."""

    name = "apps.collection"
    label = "collection"
    verbose_name = _("Collection")
