from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

from .choices import Role, ViewerLoans


class Library(TimeStampedModel):
    """A collection owned by one user and optionally shared with others."""

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="libraries"
    )
    # Read-only link for people without an account; null = not shared publicly.
    public_token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    # Viewers never see people's contact details or money; loans as the owner chooses.
    viewer_loans = models.CharField(
        max_length=10, choices=ViewerLoans.choices, default=ViewerLoans.STATUS
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("library")
        verbose_name_plural = _("libraries")

    def __str__(self) -> str:
        return self.name


class LibraryMember(TimeStampedModel):
    library = models.ForeignKey(
        "collection.Library", on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.VIEWER)

    class Meta:
        ordering = ["user__username"]
        constraints = [
            models.UniqueConstraint(fields=["library", "user"], name="unique_library_member")
        ]
        verbose_name = _("library member")
        verbose_name_plural = _("library members")

    def __str__(self) -> str:
        return f"{self.user} @ {self.library} ({self.role})"
