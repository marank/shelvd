from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class WorkFact(TimeStampedModel):
    """What an external facts source (HowLongToBeat, OpenCritic …) knows about a game,
    cached: shared by everyone, refreshed when older than the source's max age.

    `values` are the source's numbers, e.g. {"main": 12.5, "extra": 20, "complete": 41}
    (hours) or {"score": 87, "recommended": 94} (percent). `pinned` means a person chose
    the match by hand, so refreshing keeps that entry instead of searching again.
    """

    class Status(models.TextChoices):
        OK = "ok"
        MISSING = "missing"  # the source has no matching game

    work = models.ForeignKey("catalog.Work", on_delete=models.CASCADE, related_name="facts")
    source = models.CharField(max_length=20)
    external_id = models.CharField(max_length=40, blank=True)
    title = models.CharField(max_length=300, blank=True)
    url = models.URLField(blank=True)
    values = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OK)
    pinned = models.BooleanField(default=False)
    fetched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["source"]
        constraints = [
            models.UniqueConstraint(fields=["work", "source"], name="unique_fact_per_source")
        ]
        verbose_name = _("game fact")
        verbose_name_plural = _("game facts")

    def __str__(self) -> str:
        return f"{self.work_id} · {self.source}"
