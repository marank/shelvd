"""Cover search across covers sources (TheGamesDB, ScreenScraper).

Candidates reach the browser only as opaque tokens (the image URL, encrypted): some
sources put credentials into image URLs. Previews and the chosen cover are fetched by
the server – only from the source's own hosts, over https, without redirects.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from time import monotonic
from urllib.parse import urlsplit

import httpx
from django.conf import settings
from django.utils.translation import gettext as _
from ninja.errors import HttpError

from apps.catalog.models import Release
from apps.core.services.images import replace_file

from ..sources.base import CoverRecord, CoverSource, ProviderError
from ..sources.registry import cover_sources
from .integrations import decrypt, encrypt, record_error, record_ok

logger = logging.getLogger(__name__)
IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
PER_SOURCE = 24
# A whole search stays below gunicorn's 30 s timeout: after this no further source or
# title form is asked. A request started just before still gets its own read timeout
# (ScreenScraper: 20 s), so this plus that must stay under 30 s.
DEADLINE = 8.0
# Someone is waiting for the scanned game to be added.
AUTOMATIC_DEADLINE = 5.0
# Our regions that are PAL on a source's box art.
PAL_REGIONS = {"pal", "de", "uk", "fr"}


@dataclass(frozen=True)
class Candidate:
    record: CoverRecord
    token: str


# "… Special Edition", "… Game of the Year Edition", "… Remastered": sources usually list
# the plain game, so these are dropped when the full title finds nothing.
QUALIFIERS = (
    "special|deluxe|limited|collector'?s|collectors|gold|ultimate|complete|definitive|"
    "legendary|game of the year|goty|standard|premium|anniversary|launch|day one|"
    "steelbook|digital|enhanced|signature|platinum|royal|director'?s cut"
)
EDITION = re.compile(
    rf"[\s:–-]+(?:(?:{QUALIFIERS})(?:\s+edition)?|edition|remastered|remaster|hd)$",
    re.IGNORECASE,
)
BRACKETS = re.compile(r"\s*[(\[][^)\]]*[)\]]$")


def search_titles(title: str) -> list[str]:
    """The title, then shorter forms of it (without edition words) to try when nothing
    is found."""
    title = " ".join(title.replace("\u2019", "'").split())
    tries = [title, BRACKETS.sub("", title)]
    while (shorter := EDITION.sub("", tries[-1])) != tries[-1]:
        tries.append(shorter)
    return list(dict.fromkeys(t.strip() for t in tries if len(t.strip()) >= 2))


def candidates(release: Release, query: str = "") -> list[Candidate]:
    """Covers from every covers source; `query` replaces the title, else the title and
    then its shorter forms are tried (per source, until one finds something)."""
    titles = [query.strip()] if query.strip() else search_titles(release.work.title)
    found: list[Candidate] = []
    ends = monotonic() + DEADLINE
    for source in cover_sources():
        if monotonic() >= ends:
            break
        records: list[CoverRecord] = []
        try:
            for title in titles:
                if monotonic() >= ends:
                    break
                records = source.covers(title, release.platform.slug)[:PER_SOURCE]
                if records:
                    break
            record_ok(source.name)
        except ProviderError as exc:
            record_error(source.name, str(exc))
            continue
        found += [
            Candidate(r, encrypt(json.dumps({"source": source.name, "url": r.url})))
            for r in records
        ]
    return found


def _title_key(title: str) -> str:
    """A title without case, accents and punctuation ("Pokémon: X" = "pokemonx")."""
    return "".join(c for c in unicodedata.normalize("NFKD", title).casefold() if c.isalnum())


def _rank(record: CoverRecord, region: str) -> tuple[int, int]:
    """Sort key: the release's own region, then unknown ones, then the sharpest image."""
    wanted = "pal" if region in PAL_REGIONS else region
    fit = 0 if record.region == wanted else 1 if record.region in ("", "ntsc") else 2
    return fit, -(record.width or 0) * (record.height or 0)


def take_platform_cover(release: Release) -> bool:
    """Give a new release the box art of exactly this game on its platform, if a quick
    source has it. Nobody reviews this pick, so title and platform have to match: searches
    also return other games, and special editions under their own title."""
    titles = search_titles(release.work.title)
    ends = monotonic() + AUTOMATIC_DEADLINE
    for source in cover_sources():
        if not source.automatic:
            continue
        try:
            taken = _take_cover_from(source, release, titles, ends)
        except ProviderError as exc:
            record_error(source.name, str(exc))
            continue
        except HttpError:
            # The image couldn't be loaded (fetch logged why): the caller has a fallback.
            return False
        if taken is not None:
            return taken
    return False


def _take_cover_from(
    source: CoverSource, release: Release, titles: list[str], ends: float
) -> bool | None:
    """True once a cover of this source is taken, False when time is up, None when the
    source has none that fits."""
    names = {_title_key(title) for title in titles}
    slug = release.platform.slug
    for title in titles:
        if monotonic() >= ends:
            return False
        fits = [
            record
            for record in source.covers(title, slug)
            if record.platform == slug and _title_key(record.title) in names
        ]
        if fits:
            best = min(fits, key=lambda r: _rank(r, release.region))
            apply(release, encrypt(json.dumps({"source": source.name, "url": best.url})))
            record_ok(source.name)
            return True
    record_ok(source.name)
    return None


def _open(token: str) -> str:
    raw = decrypt(token)
    try:
        data = json.loads(raw) if raw else {}
    except ValueError:
        data = {}
    hosts = {h for s in cover_sources() if s.name == data.get("source") for h in s.hosts}
    url = str(data.get("url") or "")
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in hosts:
        raise HttpError(400, _("Unknown cover."))
    return url


def fetch(token: str) -> tuple[bytes, str]:
    """The image behind a token: (bytes, content type)."""
    url = _open(token)
    try:
        response = httpx.get(url, timeout=settings.PROVIDER_TIMEOUT, follow_redirects=False)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        # No URL in the log: it may contain credentials.
        logger.warning("Cover fetch failed: %s", type(exc).__name__)
        raise HttpError(502, _("The cover couldn't be loaded.")) from exc
    content_type = response.headers.get("content-type", "").split(";")[0].strip()
    if content_type not in IMAGE_TYPES or len(response.content) > settings.COVER_MAX_MB * 2**20:
        raise HttpError(502, _("The cover couldn't be loaded."))
    return response.content, content_type


def apply(release: Release, token: str) -> Release:
    content, content_type = fetch(token)
    source = json.loads(decrypt(token) or "{}").get("source", "")
    replace_file(release.cover, f"cover.{IMAGE_TYPES[content_type]}", content)
    release.cover_source = str(source)
    release.save()
    return release
