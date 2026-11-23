from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class CustomList(TimeStampedModel):
    """A user's own list of releases, e.g. "Want to borrow" or "Top 10 DS games"."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lists"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    public_token = models.CharField(max_length=64, unique=True, null=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("list")
        verbose_name_plural = _("lists")

    def __str__(self) -> str:
        return self.name


class ListEntry(TimeStampedModel):
    custom_list = models.ForeignKey(
        "sharing.CustomList", on_delete=models.CASCADE, related_name="entries"
    )
    release = models.ForeignKey("catalog.Release", on_delete=models.CASCADE, related_name="+")
    # Optional: the concrete copy in a (possibly someone else's) library.
    item = models.ForeignKey(
        "collection.Item", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    note = models.CharField(max_length=500, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["custom_list", "release"], name="unique_list_release")
        ]
        verbose_name = _("list entry")
        verbose_name_plural = _("list entries")

    def __str__(self) -> str:
        return f"{self.custom_list}: {self.release}"
