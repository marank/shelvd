from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class TrackingStatus(models.TextChoices):
    WATCHING = "watching"
    PREORDERED = "preordered"
    BOUGHT = "bought"  # paid, not arrived yet


class Tracking(TimeStampedModel):
    """A release one person is waiting for. Not part of any library until it is taken
    over; the optional target library lets its members see it (no double purchases)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trackings"
    )
    release = models.ForeignKey(
        "catalog.Release", on_delete=models.CASCADE, related_name="trackings"
    )
    status = models.CharField(
        max_length=12, choices=TrackingStatus.choices, default=TrackingStatus.WATCHING
    )
    library = models.ForeignKey(
        "collection.Library",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trackings",
    )
    shop = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    ordered_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["release__sort_date", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "release"], name="unique_user_tracking")
        ]
        verbose_name = _("tracked release")
        verbose_name_plural = _("tracked releases")

    def __str__(self) -> str:
        return f"{self.user}: {self.release} ({self.status})"
