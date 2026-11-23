from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class Person(TimeStampedModel):
    """Someone who owns copies in a library or borrows them; needs no account."""

    library = models.ForeignKey(
        "collection.Library", on_delete=models.CASCADE, related_name="people"
    )
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("person")
        verbose_name_plural = _("people")

    def __str__(self) -> str:
        return self.name
