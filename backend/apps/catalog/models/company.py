from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from .term import CatalogTerm


class Company(CatalogTerm):
    """Publisher or developer, with what an encyclopedia knows about it (Wikidata, or
    typed in): years, country, seat, website and its parent company in the catalog."""

    name = models.CharField(max_length=200, unique=True)
    external_ids = models.JSONField(default=dict, blank=True)
    founded = models.PositiveSmallIntegerField(_("founded"), null=True, blank=True)
    dissolved = models.PositiveSmallIntegerField(_("dissolved"), null=True, blank=True)
    country = models.CharField(_("country"), max_length=2, blank=True)  # ISO 3166-1 alpha-2
    headquarters = models.CharField(_("headquarters"), max_length=200, blank=True)
    website = models.URLField(_("website"), blank=True)
    parent = models.ForeignKey(
        "catalog.Company",
        verbose_name=_("parent company"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subsidiaries",
    )

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(Lower("name"), name="company_name_unique_ci")]
        verbose_name = _("company")
        verbose_name_plural = _("companies")

    def __str__(self) -> str:
        return self.name
