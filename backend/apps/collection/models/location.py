from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

from .choices import LocationKind


class Location(TimeStampedModel):
    """A place in a free hierarchy: room › shelf › box, as deep as needed."""

    library = models.ForeignKey(
        "collection.Library", on_delete=models.CASCADE, related_name="locations"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=10, choices=LocationKind.choices, default=LocationKind.OTHER)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("location")
        verbose_name_plural = _("locations")

    def __str__(self) -> str:
        return self.path

    @property
    def path(self) -> str:
        """Full path like "Office › Shelf 2 › Box A"."""
        parts: list[str] = []
        node: Location | None = self
        seen: set[object] = set()
        while node is not None and node.pk not in seen:
            seen.add(node.pk)
            parts.append(node.name)
            node = node.parent
        return " › ".join(reversed(parts))
