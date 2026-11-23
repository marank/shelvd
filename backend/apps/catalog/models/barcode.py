from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

from .review import Reviewed


class Barcode(TimeStampedModel, Reviewed):
    """A GTIN printed on a box (or another code on it, e.g. a retailer's article number in
    Code 128), mapped to the release it belongs to.

    No public database maps game barcodes reliably, so every confirmed scan is stored
    here and answers the next scan of the same code without asking a provider.
    """

    # Normalized GTIN-13 (or 8/14), or an article number in upper case.
    code = models.CharField(max_length=32, unique=True)
    release = models.ForeignKey(
        "catalog.Release", on_delete=models.CASCADE, related_name="barcodes"
    )
    source = models.CharField(max_length=30, blank=True)  # "scan", "manual", "pricecharting", …
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["code"]
        verbose_name = _("barcode")
        verbose_name_plural = _("barcodes")

    def __str__(self) -> str:
        return self.code
