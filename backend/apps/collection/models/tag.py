from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import UUIDModel


class Tag(UUIDModel):
    """A free label on copies of one library ("Steelbook", "signed" …)."""

    library = models.ForeignKey("collection.Library", on_delete=models.CASCADE, related_name="tags")
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["library", "name"], name="unique_library_tag")
        ]
        verbose_name = _("tag")
        verbose_name_plural = _("tags")

    def __str__(self) -> str:
        return self.name
