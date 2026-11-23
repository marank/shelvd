import secrets
from typing import Any

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

from .choices import DatePrecision, Region
from .dates import FAR_FUTURE, is_released, period, sort_date
from .review import Created, Reviewed

# Save these together: the image field fills width and height (its aspect ratio).
COVER_FIELDS = ["cover", "cover_width", "cover_height"]


def cover_upload_to(instance: Release, filename: str) -> str:
    """A new name for every cover: nginx lets browsers cache /media for days, so a
    replaced cover must get a new URL to show up."""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"covers/{instance.id}-{secrets.token_hex(4)}.{extension}"


class Release(TimeStampedModel, Reviewed, Created):
    """A work on one platform in one region (and edition) — what a box on the shelf is."""

    work = models.ForeignKey("catalog.Work", on_delete=models.CASCADE, related_name="releases")
    platform = models.ForeignKey(
        "catalog.Platform", on_delete=models.PROTECT, related_name="releases"
    )
    region = models.CharField(max_length=10, choices=Region.choices, default=Region.PAL)
    # Regional title if it differs from the work's title (e.g. "Pocket Monsters").
    title = models.CharField(max_length=300, blank=True)
    edition = models.CharField(max_length=200, blank=True)
    # Free text as printed: "USK 12", "PEGI 16", "Everyone 10+", "12+".
    age_rating = models.CharField(max_length=40, blank=True)
    # Code on the case/cartridge, e.g. "LA-H-A39ZA-EUR".
    product_code = models.CharField(max_length=60, blank=True)
    # Numbered limited runs (Super Rare Games #42 …).
    release_number = models.PositiveIntegerField(null=True, blank=True)
    # Most players on this platform, side by side and online (multiplayer differs per platform).
    players_offline = models.PositiveSmallIntegerField(null=True, blank=True)
    players_online = models.PositiveSmallIntegerField(null=True, blank=True)
    # First day of the release period; see release_precision ("Q3 2026" → 2026-07-01).
    release_date = models.DateField(null=True, blank=True)
    release_date_end = models.DateField(null=True, blank=True)  # only for WINDOW
    release_precision = models.CharField(
        max_length=10, choices=DatePrecision.choices, default=DatePrecision.DAY
    )
    # End of the period (far future if unknown); upcoming lists sort by it.
    sort_date = models.DateField(default=FAR_FUTURE, db_index=True)
    publisher = models.ForeignKey(
        "catalog.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="published",
    )
    # Studios that worked on this release only (a port, a remaster's extra team), besides
    # the game's developers.
    developers = models.ManyToManyField(
        "catalog.Company", blank=True, related_name="developed_releases"
    )
    cover = models.ImageField(
        upload_to=cover_upload_to,
        blank=True,
        width_field="cover_width",
        height_field="cover_height",
    )
    # Filled by Django whenever the cover is saved; lets the UI show covers uncropped.
    cover_width = models.PositiveIntegerField(null=True, blank=True, editable=False)
    cover_height = models.PositiveIntegerField(null=True, blank=True, editable=False)
    # Where the cover came from ("igdb", "upload", …), for the attribution page.
    cover_source = models.CharField(max_length=30, blank=True)
    external_ids = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["work__title", "platform__name"]
        verbose_name = _("release")
        verbose_name_plural = _("releases")

    def __str__(self) -> str:
        return f"{self.display_title} ({self.platform}, {self.region})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        start, end = period(self.release_precision, self.release_date, self.release_date_end)
        self.release_date = start
        self.release_date_end = end if self.release_precision == DatePrecision.WINDOW else None
        self.sort_date = sort_date(self.release_precision, start, end)
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = {*kwargs["update_fields"], "release_date", "sort_date"}
        super().save(*args, **kwargs)

    @property
    def cover_aspect(self) -> float | None:
        """Width / height of the cover shown (DS boxes are wider than tall, Switch
        narrow): its own, else the game's."""
        if self.cover:
            if self.cover_width and self.cover_height:
                return round(self.cover_width / self.cover_height, 4)
            return None
        return self.work.own_cover_aspect

    @property
    def cover_url(self) -> str | None:
        """Its own cover, else the game's general one."""
        if self.cover:
            return self.cover.url
        return self.work.cover.url if self.work.cover else None

    @property
    def is_released(self) -> bool:
        return is_released(
            self.release_precision,
            self.release_date,
            self.release_date_end,
            timezone.localdate(),
        )

    @property
    def display_title(self) -> str:
        return self.title or self.work.title

    @property
    def year(self) -> int | None:
        if self.release_precision == DatePrecision.TBA:
            return None
        date = self.release_date or self.work.first_release_date
        return date.year if date else None
