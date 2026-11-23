import secrets
from typing import TYPE_CHECKING

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

from .choices import MediaType
from .review import Created, Reviewed

if TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import RelatedManager

    from .release import Release
    from .work_fact import WorkFact


def work_cover_upload_to(instance: Work, filename: str) -> str:
    """A new name for every cover, so a replaced one gets a new (uncached) URL."""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"covers/works/{instance.id}-{secrets.token_hex(4)}.{extension}"


class Work(TimeStampedModel, Reviewed, Created):
    """The game (or film) itself, independent of platform and region."""

    title = models.CharField(max_length=300)
    media_type = models.CharField(max_length=10, choices=MediaType.choices, default=MediaType.GAME)
    summary = models.TextField(blank=True)
    # "The Legend of Zelda"; several for crossovers ("Mario", "Mario Kart").
    series = models.ManyToManyField("catalog.Series", blank=True, related_name="works")
    franchises = models.ManyToManyField("catalog.Franchise", blank=True, related_name="works")
    first_release_date = models.DateField(null=True, blank=True)
    # How it's played (from IGDB, in its English names): "Single player", "Co-operative" …
    game_modes = models.JSONField(default=list, blank=True)
    perspectives = models.JSONField(default=list, blank=True)  # "Third person" …
    # Language → what it covers: {"German": ["audio", "subtitles", "interface"]}.
    languages = models.JSONField(default=dict, blank=True)
    genres = models.ManyToManyField("catalog.Genre", blank=True, related_name="works")
    developers = models.ManyToManyField("catalog.Company", blank=True, related_name="developed")
    external_ids = models.JSONField(default=dict, blank=True)
    # A general cover for the game (key art), optional: shown for the game and for its
    # releases that have no cover of their own.
    cover = models.ImageField(
        upload_to=work_cover_upload_to,
        blank=True,
        width_field="cover_width",
        height_field="cover_height",
    )
    cover_width = models.PositiveIntegerField(null=True, blank=True, editable=False)
    cover_height = models.PositiveIntegerField(null=True, blank=True, editable=False)

    if TYPE_CHECKING:
        facts: RelatedManager[WorkFact]
        releases: RelatedManager[Release]

    class Meta:
        ordering = ["title"]
        verbose_name = _("work")
        verbose_name_plural = _("works")

    def __str__(self) -> str:
        return self.title

    @property
    def own_cover_aspect(self) -> float | None:
        if self.cover and self.cover_width and self.cover_height:
            return round(self.cover_width / self.cover_height, 4)
        return None

    def shown_cover(self) -> tuple[str | None, float | None]:
        """The game's cover: its own, else the first release cover (needs releases
        prefetched)."""
        if self.cover:
            return self.cover.url, self.own_cover_aspect
        covered = sorted(
            (r for r in self.releases.all() if r.cover), key=lambda r: (r.sort_date, r.pk)
        )
        return (covered[0].cover.url, covered[0].cover_aspect) if covered else (None, None)
