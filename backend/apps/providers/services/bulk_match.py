"""Matching every game of the catalog with a metadata source in one go, carefully: a game
is only matched when the source has exactly one game of that title on one of its
platforms (or it was linked before), and only what is missing or obviously wrong is
taken – empty fields, more precise dates and a first release later than the source's.
Anything else that merely differs is reported, never written. Pictures are never
touched: a game's cover is chosen by hand."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.utils.translation import override
from ninja.errors import HttpError

from apps.catalog.models import MediaType, Work

from ..sources import GameRecord
from ..sources.names import normalize
from . import metadata
from .metadata import Change


@dataclass
class Outcome:
    work: Work
    status: str  # linked | matched | unsure | none | failed
    record: GameRecord | None = None
    taken: list[Change] = field(default_factory=list)
    left: list[Change] = field(default_factory=list)
    note: str = ""


def takes(change: Change) -> bool:
    """Whether a bulk run applies the change by itself."""
    if change.cover_url or change.field in ("cover", "title"):
        return False
    if change.kind in ("fill", "precise"):
        return True
    if change.field != "first_release_date" or not change.proposed.date or not change.current.date:
        return False
    first, ours = change.proposed.date, change.current.date
    # A "first" release after the source's first one is a mistake in our data; 1 June
    # stands for "some time that year" in data entered with the year only.
    return first < ours or ((ours.month, ours.day) == (6, 1) and first.year == ours.year)


def find(work: Work, key: str) -> tuple[str, str, str]:
    """(status, external id, note): the source's game for this work, if it is sure."""
    if linked := work.external_ids.get(key):
        return "linked", str(linked), ""
    platforms = {
        str(p)
        for p in work.releases.values_list(f"platform__external_ids__{key}", flat=True)
        if p is not None
    }
    wanted = normalize(work.title)
    seen: set[str] = set()
    # Our titles are often German: the source's German title first, then its own.
    for language in ("de", "en"):
        with override(language):
            found = metadata.candidates(work, key)
        same = {
            c.record.external_id: c
            for c in found
            if normalize(c.record.title) == wanted and c.record.external_id not in seen
        }
        seen |= set(same)
        on_platform = [c for c in same.values() if c.platform_ids & platforms]
        if len(on_platform) == 1:
            return "matched", on_platform[0].record.external_id, ""
        if len(on_platform) > 1:
            ids = ", ".join(sorted(c.record.external_id for c in on_platform))
            return "unsure", "", f"several games of that title: {ids}"
        if same:
            return "unsure", "", "same title, but not on our platforms"
    return "none", "", ""


def match(work: Work, key: str, apply: bool) -> Outcome:
    """Find the work's game at the source and work out (with `apply`: take) the changes."""
    try:
        status, external_id, note = find(work, key)
        if not external_id:
            return Outcome(work, status, note=note)
        with override("de"):
            result = metadata.preview(work, key, external_id)
            taken = [c for c in result.changes if takes(c)]
            left = [c for c in result.changes if not takes(c)]
            if apply:
                metadata.apply(work, key, external_id, [c.id for c in taken])
    except HttpError as exc:  # the source didn't answer or doesn't know the game
        return Outcome(work, "failed", note=str(exc.message))
    return Outcome(work, status, result.record, taken, left)


def run(key: str, apply: bool, works: list[Work] | None = None) -> list[Outcome]:
    games = works or list(Work.objects.filter(media_type=MediaType.GAME).order_by("title"))
    return [match(work, key, apply) for work in games]
