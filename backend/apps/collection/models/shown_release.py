"""The release as a copy shows it: the catalog's values, with the copy's own where it has
them. Everything a copy is listed, sorted, grouped and filtered by reads from here."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from django.utils import timezone

from apps.catalog.models import DatePrecision, Release
from apps.catalog.models.dates import is_released, sort_date

if TYPE_CHECKING:
    from django.db.models.fields.files import ImageFieldFile

    from .item import Item


class ShownRelease:
    """Reads like a `Release`; only the overridable values come from the copy."""

    def __init__(self, item: Item) -> None:
        self._item = item
        self._release: Release = item.release

    def __getattr__(self, name: str) -> Any:
        return getattr(self._release, name)

    @property
    def _dated(self) -> bool:
        return bool(self._item.release_precision_override)

    @property
    def display_title(self) -> str:
        return self._item.title_override or self._release.display_title

    @property
    def title(self) -> str:
        return self._item.title_override or self._release.title

    @property
    def edition(self) -> str:
        return self._item.edition_override or self._release.edition

    @property
    def region(self) -> str:
        return self._item.region_override or self._release.region

    @property
    def release_precision(self) -> str:
        return self._item.release_precision_override or self._release.release_precision

    @property
    def release_date(self) -> date | None:
        return self._item.release_date_override if self._dated else self._release.release_date

    @property
    def release_date_end(self) -> date | None:
        if self._dated:
            return self._item.release_date_end_override
        return self._release.release_date_end

    @property
    def sort_date(self) -> date:
        if not self._dated:
            return self._release.sort_date
        return sort_date(self.release_precision, self.release_date, self.release_date_end)

    @property
    def is_released(self) -> bool:
        if not self._dated:
            return self._release.is_released
        return is_released(
            self.release_precision,
            self.release_date,
            self.release_date_end,
            timezone.localdate(),
        )

    @property
    def year(self) -> int | None:
        if not self._dated:
            return self._release.year
        if self.release_precision == DatePrecision.TBA:
            return None
        day = self.release_date or self._release.work.first_release_date
        return day.year if day else None

    @property
    def cover(self) -> ImageFieldFile:
        return self._item.cover_override or self._release.cover

    @property
    def cover_url(self) -> str | None:
        return self._item.cover_url

    @property
    def cover_aspect(self) -> float | None:
        return self._item.cover_aspect

    @property
    def cover_source(self) -> str:
        return "copy" if self._item.cover_override else self._release.cover_source
