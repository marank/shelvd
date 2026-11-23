"""Matching a game that's already in the catalog with any metadata source (IGDB,
Wikipedia …): what the source knows is set against what we have, field by field, and
people pick what to take. Sources answer in the reader's language where they can.

Empty fields and more precise release dates ("Q3 2026" → 15.09.2026) are suggested;
anything that merely differs is offered but not preselected, so corrections made by hand
stay unless someone deliberately replaces them."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from django.db import transaction
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from ninja.errors import HttpError

from apps.catalog.models import Company, DatePrecision, Franchise, Genre, Release, Series, Work
from apps.catalog.models.dates import period
from apps.catalog.services import terms

from ..sources import GameRecord, MetadataSource, ProviderError, metadata_source
from .importer import download_work_cover, store_play_times

# Finer first; a date only replaces one of a coarser precision.
PRECISION_RANK = {
    DatePrecision.DAY: 0,
    DatePrecision.WEEK: 1,
    DatePrecision.MONTH: 2,
    DatePrecision.QUARTER: 3,
    DatePrecision.HALF: 4,
    DatePrecision.WINDOW: 4,
    DatePrecision.YEAR: 5,
    DatePrecision.TBA: 6,
}


@dataclass
class MatchCandidate:
    """One game of the source, with every platform it came out on."""

    record: GameRecord
    platforms: list[str] = field(default_factory=list)
    platform_ids: set[str] = field(default_factory=set)


@dataclass
class Value:
    """One side of a change, in whatever form fits the field."""

    text: str = ""
    date: date | None = None
    precision: str | None = None
    image: str | None = None


@dataclass
class Change:
    id: str  # "work.summary", "<release id>.release_date"
    field: str
    kind: str  # fill (was empty) | precise (more exact date) | differs
    current: Value
    proposed: Value
    release: Release | None = None
    apply: Callable[[], None] = lambda: None
    # Covers are downloaded after the database changes, outside the transaction.
    cover_url: str = ""

    @property
    def suggested(self) -> bool:
        return self.kind != "differs"


@dataclass
class Preview:
    record: GameRecord
    changes: list[Change]


def _source(key: str) -> MetadataSource:
    source = metadata_source(key)
    if source is None:
        raise HttpError(400, _("This integration is switched off."))
    return source


def candidates(work: Work, key: str, query: str = "") -> list[MatchCandidate]:
    source = _source(key)
    try:
        records = source.search(query.strip() or work.title, language=get_language())
    except ProviderError as exc:
        raise HttpError(502, _("The source did not answer. Try again later.")) from exc
    found: dict[str, MatchCandidate] = {}
    for record in records:
        candidate = found.setdefault(record.external_id, MatchCandidate(record=record))
        if record.platform_name:
            candidate.platforms.append(record.platform_name)
        if record.platform_external_id:
            candidate.platform_ids.add(record.platform_external_id)
    return list(found.values())


def _language_lines(languages: dict[str, list[str]]) -> list[str]:
    """{"German": ["audio", "subtitles"]} → ["German (audio, subtitles)"]."""
    return [f"{name} ({', '.join(kinds)})" for name, kinds in sorted(languages.items())]


def _names(values: list[str]) -> set[str]:
    return {v.strip().casefold() for v in values}


def _work_changes(work: Work, game: GameRecord) -> list[Change]:
    return [
        *_work_text_changes(work, game),
        *_related_changes(work, game),
        *_played_changes(work, game),
        *_cover_changes(work, game),
    ]


def _work_text_changes(work: Work, game: GameRecord) -> list[Change]:
    """Title, summary and first release date."""
    changes: list[Change] = []

    def set_title() -> None:
        work.title = game.title

    def set_summary() -> None:
        work.summary = game.summary

    def set_first() -> None:
        work.first_release_date = game.first_release_date

    # Another title is only ever offered (the catalog's may be the better one).
    if game.title and work.title.strip() != game.title.strip():
        changes.append(
            Change(
                "work.title",
                "title",
                "differs",
                Value(text=work.title),
                Value(text=game.title),
                None,
                set_title,
            )
        )
    if game.summary and work.summary.strip() != game.summary.strip():
        changes.append(
            Change(
                "work.summary",
                "summary",
                "differs" if work.summary else "fill",
                Value(text=work.summary),
                Value(text=game.summary),
                None,
                set_summary,
            )
        )
    if game.first_release_date and work.first_release_date != game.first_release_date:
        changes.append(
            Change(
                "work.first_release_date",
                "first_release_date",
                "differs" if work.first_release_date else "fill",
                Value(date=work.first_release_date),
                Value(date=game.first_release_date),
                None,
                set_first,
            )
        )
    return changes


TermModel = type[Genre] | type[Company] | type[Series] | type[Franchise]


def _related_changes(work: Work, game: GameRecord) -> list[Change]:
    """Genres, developers, series and franchises: terms, offered as whole lists."""
    related: list[tuple[str, TermModel, list[str]]] = [
        ("genres", Genre, game.genres),
        ("developers", Company, game.developers),
        ("series", Series, game.series),
        ("franchises", Franchise, game.franchises),
    ]
    changes: list[Change] = []
    for name, model, proposed in related:
        current = [o.name for o in getattr(work, name).all()]
        if not proposed or _names(current) == _names(proposed):
            continue

        def set_related(
            name: str = name, model: TermModel = model, proposed: list[str] = proposed
        ) -> None:
            getattr(work, name).set(terms.by_names(model, proposed))

        changes.append(
            Change(
                f"work.{name}",
                name,
                "differs" if current else "fill",
                Value(text=", ".join(current)),
                Value(text=", ".join(proposed)),
                None,
                set_related,
            )
        )
    return changes


def _played_changes(work: Work, game: GameRecord) -> list[Change]:
    """How it's played: lists of IGDB's names, offered like the other lists."""
    played: list[tuple[str, list[str], list[str]]] = [
        ("game_modes", list(work.game_modes), game.game_modes),
        ("perspectives", list(work.perspectives), game.perspectives),
        ("languages", _language_lines(work.languages), _language_lines(game.languages)),
    ]
    changes: list[Change] = []
    for name, current, proposed in played:
        if not proposed or current == proposed:
            continue

        def set_played(name: str = name) -> None:
            setattr(work, name, getattr(game, name))

        changes.append(
            Change(
                f"work.{name}",
                name,
                "differs" if current else "fill",
                Value(text=", ".join(current)),
                Value(text=", ".join(proposed)),
                None,
                set_played,
            )
        )
    return changes


def _cover_changes(work: Work, game: GameRecord) -> list[Change]:
    """One picture for the whole game: it belongs on the work, never on a release. Only
    offered for an empty slot, as we don't know where a work's cover came from."""
    if not game.cover_url or work.cover:
        return []
    return [
        Change(
            "work.cover",
            "cover",
            "fill",
            Value(),
            Value(image=game.cover_url),
            cover_url=game.cover_url,
        )
    ]


def _release_changes(release: Release, record: GameRecord) -> list[Change]:
    return [
        *_release_date_changes(release, record),
        *_players_changes(release, record),
        *_publisher_changes(release, record),
    ]


def _date_change_kind(release: Release, released: date, precision: str) -> str:
    """ "fill", "precise" (more exact within our period), "differs" or "" (nothing to offer)."""
    if release.release_date is None:
        return "fill"
    if (
        PRECISION_RANK[DatePrecision(precision)]
        < PRECISION_RANK[DatePrecision(release.release_precision)]
    ):
        # Only a date within our period makes it more exact; one outside contradicts it.
        first, last = period(
            release.release_precision, release.release_date, release.release_date_end
        )
        inside = first is None or last is None or first <= released <= last
        return "precise" if inside else "differs"
    if precision == release.release_precision and released != release.release_date:
        return "differs"
    return ""


def _release_date_changes(release: Release, record: GameRecord) -> list[Change]:
    released, precision = record.regional_dates.get(
        release.region, (record.release_date, record.release_precision)
    )
    if released is None:
        return []
    kind = _date_change_kind(release, released, precision)
    if not kind:
        return []

    def set_date() -> None:
        release.release_date, release.release_precision = released, precision
        release.release_date_end = None

    return [
        Change(
            f"{release.pk}.release_date",
            "release_date",
            kind,
            Value(date=release.release_date, precision=release.release_precision),
            Value(date=released, precision=precision),
            release,
            set_date,
        )
    ]


def _players_changes(release: Release, record: GameRecord) -> list[Change]:
    changes: list[Change] = []
    for name in ("players_offline", "players_online"):
        now, then = getattr(release, name), getattr(record, name)
        if then is None or now == then:
            continue

        def set_players(name: str = name, then: int = then) -> None:
            setattr(release, name, then)

        changes.append(
            Change(
                f"{release.pk}.{name}",
                name,
                "differs" if now is not None else "fill",
                Value(text=str(now) if now is not None else ""),
                Value(text=str(then)),
                release,
                set_players,
            )
        )
    return changes


def _publisher_changes(release: Release, record: GameRecord) -> list[Change]:
    current = release.publisher.name if release.publisher else ""
    if not record.publisher or current.casefold() == record.publisher.casefold():
        return []

    def set_publisher() -> None:
        release.publisher = terms.by_name(Company, record.publisher)

    return [
        Change(
            f"{release.pk}.publisher",
            "publisher",
            "differs" if current else "fill",
            Value(text=current),
            Value(text=record.publisher),
            release,
            set_publisher,
        )
    ]


def preview(work: Work, key: str, external_id: str) -> Preview:
    """What the source's game would change, field by field (only real differences)."""
    source = _source(key)
    try:
        records = source.get_all(external_id, language=get_language())
    except ProviderError as exc:
        raise HttpError(502, _("The source did not answer. Try again later.")) from exc
    if not records:
        raise HttpError(404, _("The source does not know this game."))
    by_platform = {r.platform_external_id: r for r in records if r.platform_external_id}
    changes = _work_changes(work, records[0])
    for release in work.releases.select_related("platform", "publisher").order_by(
        "platform__name", "region", "edition"
    ):
        platform_id = release.platform.external_ids.get(key)
        record = by_platform.get(str(platform_id)) if platform_id is not None else None
        if record is not None:
            changes += _release_changes(release, record)
    return Preview(record=records[0], changes=changes)


def apply(work: Work, key: str, external_id: str, chosen: list[str]) -> list[str]:
    """Link the work to the source's game and apply the chosen changes. They are worked
    out again here, so a client can only pick, never inject values. Returns the ids
    that were applied."""
    result = preview(work, key, external_id)
    picked = [c for c in result.changes if c.id in set(chosen)]
    with transaction.atomic():
        work.external_ids = {**work.external_ids, key: result.record.external_id}
        for change in picked:
            change.apply()
        work.save()
        # Its play times and page are facts of the game: always taken along.
        store_play_times(work, result.record)
        for release in {c.release.pk: c.release for c in picked if c.release}.values():
            release.save()
    applied = [c.id for c in picked if not c.cover_url]
    applied.extend(
        change.id
        for change in picked
        if change.cover_url and download_work_cover(work, change.cover_url)
    )
    return applied
