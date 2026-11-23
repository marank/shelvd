"""What people enter themselves waits for an admin: the review status of catalog entries."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ReviewStatus(models.TextChoices):
    PENDING = "pending", _("unreviewed")
    APPROVED = "approved", _("reviewed")


class Reviewed(models.Model):
    """Usable right away; `pending` until an admin approves it. Existing and admin-made
    entries are approved."""

    review_status = models.CharField(
        max_length=10, choices=ReviewStatus.choices, default=ReviewStatus.APPROVED, db_index=True
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    @property
    def pending(self) -> bool:
        return self.review_status == ReviewStatus.PENDING


class Created(models.Model):
    """Who entered it (the creator may still edit it while it is unreviewed)."""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        abstract = True
