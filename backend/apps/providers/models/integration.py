from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class Integration(TimeStampedModel):
    """One external service's configuration, edited by admins in the app.

    `options` are plain settings; `secrets` (keys, passwords) are stored encrypted
    (services.integrations) and never sent back to the browser in clear text.
    """

    key = models.CharField(max_length=40, unique=True)  # services.integrations.DEFINITIONS
    enabled = models.BooleanField(default=False)
    options = models.JSONField(default=dict, blank=True)
    secrets = models.TextField(blank=True)
    last_ok_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    # When the scheduler last ran this integration's periodic job.
    last_run_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["key"]
        verbose_name = _("integration")
        verbose_name_plural = _("integrations")

    def __str__(self) -> str:
        return self.key
