from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from .term import CatalogTerm


class Series(CatalogTerm):
    """A game series ("Super Mario", "The Legend of Zelda: Ocarina of Time"); a game can be
    in several. The brand above it is its `Franchise`."""

    name = models.CharField(max_length=200)
    external_ids = models.JSONField(default=dict, blank=True)
    # The brand it belongs to ("Mario Kart" → "Mario"), by hand or from Wikidata.
    franchise = models.ForeignKey(
        "catalog.Franchise",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="series",
        verbose_name=_("franchise"),
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("series")
        verbose_name_plural = _("series")
        constraints = [
            models.UniqueConstraint(Lower("name"), name="series_name_unique_ci"),
        ]

    def __str__(self) -> str:
        return self.name
