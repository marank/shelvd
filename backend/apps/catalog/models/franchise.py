from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from .term import CatalogTerm


class Franchise(CatalogTerm):
    """The brand a game belongs to ("Mario"), wider than its series ("Super Mario",
    "Mario Kart"); a game can be in several."""

    name = models.CharField(max_length=200)
    external_ids = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("franchise")
        verbose_name_plural = _("franchises")
        constraints = [
            models.UniqueConstraint(Lower("name"), name="franchise_name_unique_ci"),
        ]

    def __str__(self) -> str:
        return self.name
