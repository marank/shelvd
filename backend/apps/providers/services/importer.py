"""Write provider records into the catalog (work, release, companies, genres, cover)."""

from __future__ import annotations

import logging

import httpx
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import (
    COVER_FIELDS,
    Company,
    Franchise,
    Genre,
    Platform,
    Release,
    Series,
    Work,
    WorkFact,
)
from apps.catalog.services import terms
from apps.catalog.services.review import stamp
from apps.core.services.images import replace_file

from ..sources import GameRecord
from .covers import take_platform_cover

logger = logging.getLogger(__name__)

IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def platform_for(record: GameRecord) -> Platform | None:
    if not record.platform_external_id:
        return None
    return Platform.objects.filter(
        **{f"external_ids__{record.provider}": int(record.platform_external_id)}
    ).first()


def import_record(
    record: GameRecord, platform: Platform, region: str, user: User | None = None
) -> Release:
    """Find or create the work and the (platform, region) release for a record. The
    record's cover (IGDB) is one picture for the whole game, so it goes on the work; the
    release gets box art of its platform if there is one, else it shows the work's."""
    release = _store_record(record, platform, region, user)
    store_play_times(release.work, record)
    # After the transaction: this waits for other services.
    if record.cover_url and not release.work.cover:
        download_work_cover(release.work, record.cover_url)
    if not release.cover:
        take_platform_cover(release)
    return release


@transaction.atomic
def _store_record(
    record: GameRecord, platform: Platform, region: str, user: User | None
) -> Release:
    # Straight from the source: reviewed, whoever brought it in.
    work = Work.objects.filter(**{f"external_ids__{record.provider}": record.external_id}).first()
    if work is None:
        work = Work(
            title=record.title,
            summary=record.summary,
            first_release_date=record.first_release_date,
            game_modes=record.game_modes,
            perspectives=record.perspectives,
            languages=record.languages,
            external_ids={record.provider: record.external_id},
        )
        stamp(work, user, trusted=True)
        work.save()
        work.series.set(terms.by_names(Series, record.series))
        work.franchises.set(terms.by_names(Franchise, record.franchises))
        work.genres.set(terms.by_names(Genre, record.genres))
        work.developers.set(terms.by_names(Company, record.developers))

    release = Release.objects.filter(
        work=work, platform=platform, region=region, edition=""
    ).first()
    if release is None:
        release = Release(
            work=work,
            platform=platform,
            region=region,
            # This region's date if IGDB knows it, else the best known one.
            release_date=record.regional_dates.get(region, (record.release_date, ""))[0],
            release_precision=record.regional_dates.get(region, (None, record.release_precision))[
                1
            ],
            publisher=terms.by_name(Company, record.publisher) if record.publisher else None,
            players_offline=record.players_offline,
            players_online=record.players_online,
            external_ids={record.provider: record.external_id},
        )
        stamp(release, user, trusted=True)
        release.save()
    return release


def store_play_times(work: Work, record: GameRecord) -> None:
    """The source's own play times (IGDB's time to beat) as a fact of the game, beside
    HowLongToBeat's; its page address comes along (a link on the game's page)."""
    if not record.play_times and not record.url:
        return
    WorkFact.objects.update_or_create(
        work=work,
        source=record.provider,
        defaults={
            "external_id": record.external_id,
            "title": record.title,
            "url": record.url,
            "values": record.play_times,
            "status": WorkFact.Status.OK,
            "fetched_at": timezone.now(),
        },
    )


def fetch_image(url: str, owner: object, follow_redirects: bool = True) -> tuple[bytes, str] | None:
    """The image's bytes and file extension, or None if it can't be used."""
    limit = settings.COVER_MAX_MB * 1024 * 1024
    try:
        response = httpx.get(
            url, timeout=settings.PROVIDER_TIMEOUT, follow_redirects=follow_redirects
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Cover download failed for %s: %s", owner, exc)
        return None
    content_type = response.headers.get("content-type", "").split(";")[0].strip()
    extension = IMAGE_TYPES.get(content_type)
    if extension is None or len(response.content) > limit:
        logger.warning(
            "Cover for %s rejected (%s, %d bytes)", owner, content_type, len(response.content)
        )
        return None
    return response.content, extension


def download_cover(
    release: Release, url: str, source: str, *, follow_redirects: bool = True
) -> bool:
    """Store the cover locally (providers' image hosts are not meant for hotlinking)."""
    image = fetch_image(url, release, follow_redirects)
    if image is None:
        return False
    replace_file(release.cover, f"cover.{image[1]}", image[0])
    release.cover_source = source
    release.save(update_fields=[*COVER_FIELDS, "cover_source", "updated_at"])
    return True


def download_work_cover(work: Work, url: str) -> bool:
    """Store the game's general cover locally."""
    image = fetch_image(url, work)
    if image is None:
        return False
    replace_file(work.cover, f"cover.{image[1]}", image[0])
    work.save(update_fields=[*COVER_FIELDS, "updated_at"])
    return True
