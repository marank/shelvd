from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from .term import CatalogTerm


class Genre(CatalogTerm):
    name = models.CharField(max_length=100, unique=True)
    external_ids = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(Lower("name"), name="genre_name_unique_ci")]
        verbose_name = _("genre")
        verbose_name_plural = _("genres")

    def __str__(self) -> str:
        return self.name
