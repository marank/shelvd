import secrets
from functools import cached_property

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import DatePrecision, Region
from apps.core.models import TimeStampedModel

from .choices import Completeness, Condition, ItemFormat, ItemStatus, PlayStatus
from .shown_release import ShownRelease


def item_cover_upload_to(instance: Item, filename: str) -> str:
    """A new name for every cover (see catalog.models.release.cover_upload_to)."""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"item-covers/{instance.id}-{secrets.token_hex(4)}.{extension}"


class Item(TimeStampedModel):
    """One copy of a release in a library."""

    library = models.ForeignKey(
        "collection.Library", on_delete=models.CASCADE, related_name="items"
    )
    release = models.ForeignKey("catalog.Release", on_delete=models.PROTECT, related_name="items")
    format = models.CharField(
        max_length=10, choices=ItemFormat.choices, default=ItemFormat.PHYSICAL
    )
    status = models.CharField(max_length=12, choices=ItemStatus.choices, default=ItemStatus.OWNED)
    condition = models.CharField(max_length=12, choices=Condition.choices, blank=True)
    completeness = models.CharField(max_length=14, choices=Completeness.choices, blank=True)
    play_status = models.CharField(max_length=10, choices=PlayStatus.choices, blank=True)
    location = models.ForeignKey(
        "collection.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )
    # Who the copy belongs to (e.g. which family member); empty = the library owner.
    owner = models.ForeignKey(
        "collection.Person", on_delete=models.SET_NULL, null=True, blank=True, related_name="owned"
    )
    acquired_on = models.DateField(null=True, blank=True)
    purchase_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    # What the copy is worth today (collector's value), maintained by hand or by an import.
    current_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tags = models.ManyToManyField("collection.Tag", blank=True, related_name="items")
    # Ids in other collection tools ({"<tool>": "<id>"}), set by importers (add-ons);
    # re-imports update by them.
    source_ids = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    # Where this copy differs from its release (empty = as the release): the library's own
    # title, cover, edition, region and date. The shared catalog stays untouched; `shown`
    # combines both.
    title_override = models.CharField(max_length=300, blank=True)
    cover_override = models.ImageField(
        upload_to=item_cover_upload_to,
        blank=True,
        width_field="cover_override_width",
        height_field="cover_override_height",
    )
    cover_override_width = models.PositiveIntegerField(null=True, blank=True, editable=False)
    cover_override_height = models.PositiveIntegerField(null=True, blank=True, editable=False)
    edition_override = models.CharField(max_length=200, blank=True)
    region_override = models.CharField(max_length=10, choices=Region.choices, blank=True)
    # A date of its own needs a precision; without one the release's date applies.
    release_precision_override = models.CharField(
        max_length=10, choices=DatePrecision.choices, blank=True
    )
    release_date_override = models.DateField(null=True, blank=True)
    release_date_end_override = models.DateField(null=True, blank=True)

    # What a viewer may see of the active loan ("all", or ViewerLoans); set per request.
    loan_visibility: str = "all"

    class Meta:
        ordering = ["release__work__title", "release__platform__name"]
        verbose_name = _("item")
        verbose_name_plural = _("items")

    def __str__(self) -> str:
        return str(self.release)

    @cached_property
    def shown(self) -> ShownRelease:
        """The release with this copy's own values: what lists, sorting and filters use."""
        return ShownRelease(self)

    @property
    def overrides(self) -> list[str]:
        """Which of the release's values this copy replaces."""
        present = {
            "title": bool(self.title_override),
            "cover": bool(self.cover_override),
            "edition": bool(self.edition_override),
            "region": bool(self.region_override),
            "release_date": bool(self.release_precision_override),
        }
        return [name for name, on in present.items() if on]

    @property
    def display_title(self) -> str:
        return self.title_override or self.release.display_title

    @property
    def cover_aspect(self) -> float | None:
        if self.cover_override and self.cover_override_width and self.cover_override_height:
            return round(self.cover_override_width / self.cover_override_height, 4)
        return self.release.cover_aspect

    @property
    def cover_url(self) -> str | None:
        if self.cover_override:
            return self.cover_override.url
        return self.release.cover_url
