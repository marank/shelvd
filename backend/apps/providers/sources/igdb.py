"""IGDB (igdb.com, owned by Twitch): metadata, regional release dates and covers.

Free for non-commercial use with a Twitch application (client id + secret); requests
go through the backend because IGDB sends no CORS headers. About 4 requests/second.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
import pycountry
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext as _

from ..services.integrations import Config, config
from .base import (
    METADATA_FIELDS,
    CompanyFacts,
    DescriptionRecord,
    EntryRef,
    GameRecord,
    GetFromAll,
    ImageOption,
    PlatformFacts,
    ProviderError,
)
from .names import normalize, variants, without_generic

TOKEN_URL = "https://id.twitch.tv/oauth2/token"  # noqa: S105  endpoint address, not a secret
API_URL = "https://api.igdb.com/v4"
COVER_URL = "https://images.igdb.com/igdb/image/upload/t_cover_big_2x/{image_id}.jpg"
LOGO_URL = "https://images.igdb.com/igdb/image/upload/t_logo_med/{image_id}.png"
IMAGE_HOST = "images.igdb.com"
IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
IMAGE_MAX_BYTES = 2 * 1024 * 1024  # what a term's picture may have
TOKEN_CACHE_KEY = "providers:igdb:token"  # noqa: S105  cache key name, not a secret
RETRIES = 4
RETRY_WAIT = 1.0  # seconds, more on every further try


class _TooManyRequestsError(Exception):
    """IGDB's rate limit (HTTP 429)."""


# Where answers are kept while `saved_answers` is on (bulk matching), else None.
_ANSWERS: ContextVar[Path | None] = ContextVar("igdb_answers", default=None)


@contextmanager
def saved_answers(directory: Path) -> Iterator[None]:
    """Keep every answer IGDB gives as a file and answer the same query from it again:
    a bulk run can be repeated (dry run, then for real) without asking IGDB twice. The
    files hold public game data only; delete the directory to ask afresh."""
    directory.mkdir(parents=True, exist_ok=True)
    token = _ANSWERS.set(directory)
    try:
        yield
    finally:
        _ANSWERS.reset(token)


COMPANY_FIELDS = (
    "name,description,country,start_date,logo.image_id,parent.name,websites.url,websites.type,"
    "websites.category"
)
OFFICIAL_WEBSITE = 1  # website type / category "official"
PLATFORM_FIELDS = (
    "name,abbreviation,alternative_name,generation,summary,platform_logo.image_id,"
    "versions.name,versions.summary,versions.platform_logo.image_id,"
    "versions.platform_version_release_dates.date,versions.companies.company.name,"
    "versions.companies.manufacturer"
)

# IGDB release_region ids → our Region values.
REGIONS = {
    1: "pal",  # europe
    2: "na",
    3: "pal",  # australia
    4: "pal",  # new zealand
    5: "jp",
    6: "asia",  # china
    7: "asia",
    8: "world",
    9: "kr",
    10: "other",  # brazil
}

# Several IGDB regions are one of ours (PAL: Europe, Australia, New Zealand). The shelf
# is European, so Europe's date wins over Australia's, which is often months earlier.
EUROPE = 1


def _region_rank(entry: dict[str, Any]) -> tuple[bool, int]:
    """Sort key: Europe before the other PAL regions, then the earliest date."""
    released = entry.get("date")
    return entry.get("release_region") != EUROPE, released if isinstance(released, int) else 2**40


# IGDB release date category → our DatePrecision ("Q3 2026", "TBD", …).
PRECISIONS = {
    0: "day",
    1: "month",
    2: "year",
    3: "quarter",
    4: "quarter",
    5: "quarter",
    6: "quarter",
    7: "tba",
}

# IGDB's fixed genre list in German (other languages keep IGDB's English names).
GENRES_DE = {
    "Adventure": "Adventure",
    "Arcade": "Arcade",
    "Card & Board Game": "Karten- und Brettspiel",
    "Fighting": "Kampfspiel",
    "Hack and slash/Beat 'em up": "Hack and Slash/Beat 'em up",
    "Indie": "Indie",
    "MOBA": "MOBA",
    "Music": "Musik",
    "Pinball": "Flipper",
    "Platform": "Jump 'n' Run",
    "Point-and-click": "Point-and-Click",
    "Puzzle": "Puzzle",
    "Quiz/Trivia": "Quiz",
    "Racing": "Rennspiel",
    "Real Time Strategy (RTS)": "Echtzeitstrategie",
    "Role-playing (RPG)": "Rollenspiel",
    "Shooter": "Shooter",
    "Simulator": "Simulation",
    "Sport": "Sport",
    "Strategy": "Strategie",
    "Tactical": "Taktik",
    "Turn-based strategy (TBS)": "Rundenstrategie",
    "Visual Novel": "Visual Novel",
}
# How IGDB's alternative names mark a language's title ("German title").
TITLE_COMMENTS = {"de": "german"}

FIELDS = (
    "name,alternative_names.name,alternative_names.comment,summary,first_release_date,cover.image_id,genres.name,"
    "involved_companies.company.name,involved_companies.developer,involved_companies.publisher,"
    "platforms.name,release_dates.platform,release_dates.date,release_dates.release_region,"
    "release_dates.category,url,franchises.name,collections.name,game_modes.name,"
    "player_perspectives.name,multiplayer_modes.platform,multiplayer_modes.offlinemax,"
    "multiplayer_modes.offlinecoopmax,multiplayer_modes.onlinemax,multiplayer_modes.onlinecoopmax,"
    "language_supports.language.name,language_supports.language_support_type.name"
)
# IGDB's time to beat (seconds) → our names (hours).
PLAY_TIMES = {"hastily": "main", "normally": "extra", "completely": "complete"}


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _date(timestamp: Any) -> date | None:
    if not isinstance(timestamp, int):
        return None
    return datetime.fromtimestamp(timestamp, tz=UTC).date()


class IGDBSource(GetFromAll):
    name = "igdb"
    catalog = True
    fields = METADATA_FIELDS

    def __init__(self, cfg: Config | None = None) -> None:
        self.cfg = cfg or config("igdb")
        self.client_id = str(self.cfg.value("client_id") or "")
        # One token per client id: new credentials don't reuse the old one.
        self.token_key = f"{TOKEN_CACHE_KEY}:{self.client_id}"

    def enabled(self) -> bool:
        return self.cfg.active

    # --- HTTP -----------------------------------------------------------------------
    def _token(self) -> str:
        token = cache.get(self.token_key)
        if isinstance(token, str):
            return token
        try:
            # In the form body, not the URL: URLs end up in logs and error messages.
            response = httpx.post(
                TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": str(self.cfg.value("client_secret") or ""),
                    "grant_type": "client_credentials",
                },
                timeout=settings.PROVIDER_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"IGDB authentication failed: {exc}") from exc
        token = str(data["access_token"])
        # Renew a minute early; Twitch tokens live for about 60 days.
        cache.set(self.token_key, token, max(int(data.get("expires_in", 3600)) - 60, 60))
        return token

    def _query(self, endpoint: str, body: str) -> list[dict[str, Any]]:
        directory = _ANSWERS.get()
        if directory is None:
            return self._ask(endpoint, body)
        key = hashlib.sha256(f"{endpoint}\n{body}".encode()).hexdigest()
        path = directory / f"{endpoint}-{key[:32]}.json"
        if path.exists():
            saved: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
            return saved
        data = self._ask(endpoint, body)
        path.write_text(json.dumps(data), encoding="utf-8")
        return data

    def _ask(self, endpoint: str, body: str) -> list[dict[str, Any]]:
        # IGDB allows about four requests a second and answers 429 beyond: wait, try again.
        for attempt in range(RETRIES):
            try:
                return self._post(endpoint, body)
            except _TooManyRequestsError:
                time.sleep(RETRY_WAIT * (attempt + 1))
        raise ProviderError("IGDB request failed: too many requests.")

    def _post(self, endpoint: str, body: str) -> list[dict[str, Any]]:
        try:
            response = httpx.post(
                f"{API_URL}/{endpoint}",
                content=body,
                headers={
                    "Client-ID": self.client_id,
                    "Authorization": f"Bearer {self._token()}",
                },
                timeout=settings.PROVIDER_TIMEOUT,
            )
            if response.status_code == 401:
                cache.delete(self.token_key)
            if response.status_code == 429:
                raise _TooManyRequestsError
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"IGDB request failed: {exc}") from exc
        if not isinstance(data, list):
            raise ProviderError("IGDB returned an unexpected response.")
        return data

    def test(self) -> str:
        self._query("platforms", "fields id; limit 1;")
        return _("OK")

    # --- MetadataSource ---------------------------------------------------------------
    def search(
        self, query: str, platform_external_id: str | None = None, language: str = "en"
    ) -> list[GameRecord]:
        where = f" where platforms = ({int(platform_external_id)});" if platform_external_id else ""
        games = self._query("games", f"search {_quote(query)}; fields {FIELDS};{where} limit 15;")
        records: list[GameRecord] = []
        for game in games:
            records.extend(self._records(game, platform_external_id, language))
        return records

    def get_all(
        self, external_id: str, platform_external_id: str | None = None, language: str = "en"
    ) -> list[GameRecord]:
        games = self._query("games", f"fields {FIELDS}; where id = {int(external_id)};")
        if not games:
            return []
        # Only for one game (search results go without): another request.
        times = self._query(
            "game_time_to_beats",
            f"fields hastily,normally,completely; where game_id = {int(external_id)};",
        )
        return self._records(games[0], platform_external_id, language, times[0] if times else {})

    # --- DescriptionSource (companies and platforms: IGDB's series have no text) ------
    def describe(self, query: str, kind: str, language: str = "en") -> list[DescriptionRecord]:
        """Companies whose name contains the query, exactly that name first; a name that
        finds none exactly is searched again without its legal form and run together, and
        one that finds nothing at all without "Studio", "Games" … (never a sure match).
        Platforms by name, alternative name or abbreviation."""
        if kind == "platforms" and query.strip():
            return self._describe_platforms(query.strip())
        if kind != "companies" or not query.strip():
            return []
        wanted = normalize(query)
        found = self._find_companies(query, wanted)

        def rank(company: dict[str, Any]) -> tuple[bool, int]:
            name = str(company.get("name", ""))
            return normalize(name) != wanted, len(name)

        companies = sorted(found.values(), key=rank)
        return [self._company_record(c, wanted) for c in companies[:10]]

    def _find_companies(self, query: str, wanted: str) -> dict[int, dict[str, Any]]:
        """Companies by id: the query and its variants until one matches exactly, else
        those containing the query without generic words."""
        found: dict[int, dict[str, Any]] = {}

        def add(where: str) -> None:
            for company in self._companies(f"where {where}; limit 20;"):
                found.setdefault(int(company["id"]), company)

        for name in [query.strip(), *variants(query)]:
            # Exactly the name (ignoring case) first: a common one ("Nintendo") is part
            # of more names than one page holds.
            add(f"name ~ {_quote(name)}")
            add(f"name ~ *{_quote(name)}*")
            if any(normalize(str(c.get("name", ""))) == wanted for c in found.values()):
                break
        if not found and (core := without_generic(query)):
            add(f"name ~ *{_quote(core)}*")
        return found

    def description(
        self, external_id: str, language: str = "en", kind: str = ""
    ) -> DescriptionRecord | None:
        if not external_id.isdigit() or kind not in ("", "companies", "platforms"):
            return None
        if kind == "platforms":
            platforms = self._platforms(f"where id = {int(external_id)};")
            return self._platform_record(platforms[0], "", full=True) if platforms else None
        companies = self._companies(f"where id = {int(external_id)};")
        return self._company_record(companies[0], "", full=True) if companies else None

    def _platforms(self, where: str) -> list[dict[str, Any]]:
        return self._query("platforms", f"fields {PLATFORM_FIELDS}; {where}")

    def _describe_platforms(self, query: str) -> list[DescriptionRecord]:
        wanted = normalize(query)
        q = _quote(query)
        platforms = self._platforms(
            f"where name ~ *{q}* | alternative_name ~ *{q}* | abbreviation ~ {q}; limit 20;"
        )

        def rank(platform: dict[str, Any]) -> tuple[bool, int]:
            name = str(platform.get("name", ""))
            return not self._platform_fits(platform, wanted), len(name)

        return [self._platform_record(p, wanted) for p in sorted(platforms, key=rank)[:10]]

    @staticmethod
    def _platform_fits(platform: dict[str, Any], wanted: str) -> bool:
        names = (platform.get(k) for k in ("name", "abbreviation", "alternative_name"))
        return bool(wanted) and wanted in {normalize(str(n)) for n in names if n}

    @staticmethod
    def _first_version(platform: dict[str, Any]) -> dict[str, Any]:
        """The original model ("Initial version"); none if IGDB doesn't say which it is –
        the first listed may be any (PC: "Windows 2.0")."""
        versions = platform.get("versions") or []
        return next((v for v in versions if "initial" in str(v.get("name", "")).lower()), {})

    def _platform_record(
        self, platform: dict[str, Any], wanted: str, full: bool = False
    ) -> DescriptionRecord:
        """A platform as an entry: its text (or its original model's) is English; with
        `full` its logo and facts too."""
        version = self._first_version(platform)
        text = str(platform.get("summary") or version.get("summary") or "").strip()
        if text:
            text = f"{text}\n\nSource: IGDB"  # English, like IGDB's texts
        logo = platform.get("platform_logo") or version.get("platform_logo") or {}
        logo_url = LOGO_URL.format(image_id=logo["image_id"]) if logo.get("image_id") else ""
        generation = platform.get("generation")
        return DescriptionRecord(
            source=self.name,
            external_id=str(platform["id"]),
            title=str(platform.get("name", "")),
            label=_("Generation %(n)s") % {"n": generation} if generation else _("Platform"),
            text=text,
            language="en" if text else "",
            image_url=logo_url,
            confident=self._platform_fits(platform, wanted),
            texts={"en": text} if full and text else {},
            images=(ImageOption(logo_url, _("Logo")),) if full and logo_url else (),
            platform=self._platform_facts(platform, version) if full else None,
        )

    @staticmethod
    def _platform_facts(platform: dict[str, Any], version: dict[str, Any]) -> PlatformFacts:
        """Abbreviation, first release year, generation and maker of a platform."""
        years = [
            d.year
            for v in platform.get("versions") or []
            for entry in v.get("platform_version_release_dates") or []
            if (d := _date(entry.get("date")))
        ]
        maker = next(
            (c["company"] for c in version.get("companies") or [] if c.get("manufacturer")),
            None,
        )
        generation = platform.get("generation")
        return PlatformFacts(
            short_name=str(platform.get("abbreviation") or "")[:20],
            released=min(years) if years else None,
            generation=generation if isinstance(generation, int) else None,
            manufacturer=EntryRef(str(maker["id"]), (str(maker.get("name", "")),))
            if isinstance(maker, dict) and maker.get("id")
            else None,
        )

    def image(self, url: str) -> bytes:
        if urlsplit(url).scheme != "https" or urlsplit(url).hostname != IMAGE_HOST:
            raise ProviderError("Not an IGDB image.")
        try:
            response = httpx.get(url, timeout=settings.PROVIDER_TIMEOUT, follow_redirects=False)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"IGDB image request failed: {exc}") from exc
        content_type = response.headers.get("content-type", "").split(";")[0].strip()
        if content_type not in IMAGE_TYPES or len(response.content) > IMAGE_MAX_BYTES:
            raise ProviderError("IGDB returned no usable image.")
        return response.content

    def _companies(self, where: str) -> list[dict[str, Any]]:
        return self._query("companies", f"fields {COMPANY_FIELDS}; {where}")

    def _company_record(
        self, company: dict[str, Any], wanted: str, full: bool = False
    ) -> DescriptionRecord:
        """A company as an entry: IGDB's text is English; with `full` its facts too."""
        name = str(company.get("name", ""))
        text = str(company.get("description") or "").strip()
        if text:
            text = f"{text}\n\nSource: IGDB"  # English, like IGDB's texts
        logo = company.get("logo") or {}
        logo_url = LOGO_URL.format(image_id=logo["image_id"]) if logo.get("image_id") else ""
        country = self._country(company.get("country"))
        started = _date(company.get("start_date"))
        return DescriptionRecord(
            source=self.name,
            external_id=str(company["id"]),
            title=name,
            label=_("Company, founded %(year)s") % {"year": started.year}
            if started
            else _("Company"),
            text=text,
            language="en" if text else "",
            image_url=logo_url,
            confident=bool(wanted) and normalize(name) == wanted,
            texts={"en": text} if full and text else {},
            images=(ImageOption(logo_url, _("Logo")),) if full and logo_url else (),
            company=self._company_facts(company, country, started) if full else None,
        )

    @staticmethod
    def _country(numeric: Any) -> str:
        """IGDB's ISO 3166-1 numeric country code as alpha-2 ("392" → "JP")."""
        if not isinstance(numeric, int):
            return ""
        found = pycountry.countries.get(numeric=f"{numeric:03d}")
        return str(found.alpha_2) if found else ""

    @staticmethod
    def _company_facts(company: dict[str, Any], country: str, started: date | None) -> CompanyFacts:
        website = next(
            (
                str(w["url"])
                for w in company.get("websites") or []
                if OFFICIAL_WEBSITE in (w.get("type"), w.get("category")) and w.get("url")
            ),
            "",
        )
        parent = company.get("parent") or {}
        return CompanyFacts(
            founded=started.year if started else None,
            country=country,
            website=website,
            parent=EntryRef(str(parent["id"]), (str(parent.get("name", "")),))
            if parent.get("id")
            else None,
        )

    # --- mapping ------------------------------------------------------------------------
    @staticmethod
    def _title(game: dict[str, Any], language: str) -> str:
        """The title in that language if IGDB lists one ("German title"), else its own."""
        marker = TITLE_COMMENTS.get(language.split("-")[0])
        if marker:
            for alt in game.get("alternative_names") or []:
                if marker in str(alt.get("comment", "")).casefold() and alt.get("name"):
                    return str(alt["name"])
        return str(game.get("name", ""))

    @staticmethod
    def _genres(game: dict[str, Any], language: str) -> list[str]:
        names = [str(g["name"]) for g in game.get("genres") or [] if g.get("name")]
        if language.split("-")[0] == "de":
            return [GENRES_DE.get(name, name) for name in names]
        return names

    def _records(
        self,
        game: dict[str, Any],
        only_platform: str | None,
        language: str = "en",
        times: dict[str, Any] | None = None,
    ) -> list[GameRecord]:
        companies = game.get("involved_companies") or []
        publishers = [c["company"]["name"] for c in companies if c.get("publisher")]
        developers = [c["company"]["name"] for c in companies if c.get("developer")]
        cover = game.get("cover") or {}
        cover_url = COVER_URL.format(image_id=cover["image_id"]) if cover.get("image_id") else ""
        platforms = game.get("platforms") or [{"id": None, "name": ""}]

        def names(key: str) -> list[str]:
            return [str(x["name"]) for x in game.get(key) or [] if x.get("name")]

        play_times = {
            ours: round(int(seconds) / 3600, 1)
            for theirs, ours in PLAY_TIMES.items()
            if isinstance(seconds := (times or {}).get(theirs), int) and seconds > 0
        }
        records = []
        for platform in platforms:
            platform_id = str(platform["id"]) if platform.get("id") is not None else None
            if only_platform and platform_id != str(only_platform):
                continue
            region, released, precision = self._first_release(game, platform.get("id"))
            regional = self._regional_dates(game, platform.get("id"))
            records.append(
                GameRecord(
                    provider=self.name,
                    external_id=str(game["id"]),
                    title=self._title(game, language),
                    platform_external_id=platform_id,
                    platform_name=str(platform.get("name", "")),
                    region=region,
                    release_date=released,
                    release_precision=precision,
                    regional_dates=regional,
                    first_release_date=_date(game.get("first_release_date")),
                    publisher=publishers[0] if publishers else "",
                    developers=developers,
                    genres=self._genres(game, language),
                    summary=str(game.get("summary", "")),
                    cover_url=cover_url,
                    url=str(game.get("url", "")),
                    # IGDB's collections are what its site calls series.
                    series=names("collections"),
                    franchises=names("franchises"),
                    game_modes=names("game_modes"),
                    perspectives=names("player_perspectives"),
                    languages=self._languages(game),
                    players_offline=self._players(game, platform.get("id"), "offline"),
                    players_online=self._players(game, platform.get("id"), "online"),
                    play_times=play_times,
                )
            )
        return records

    @staticmethod
    def _languages(game: dict[str, Any]) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for entry in game.get("language_supports") or []:
            name = (entry.get("language") or {}).get("name")
            kind = (entry.get("language_support_type") or {}).get("name")
            if name and kind:
                kinds = result.setdefault(str(name), [])
                if str(kind).lower() not in kinds:
                    kinds.append(str(kind).lower())
        return result

    @staticmethod
    def _players(game: dict[str, Any], platform_id: Any, where: str) -> int | None:
        """Most players on that platform, side by side (`offline`) or online."""
        counts = [
            int(value)
            for mode in game.get("multiplayer_modes") or []
            if mode.get("platform") == platform_id
            for key in (f"{where}max", f"{where}coopmax")
            if isinstance(value := mode.get(key), int) and value > 0
        ]
        return max(counts) if counts else None

    @staticmethod
    def _regional_dates(
        game: dict[str, Any], platform_id: Any
    ) -> dict[str, tuple[date | None, str]]:
        result: dict[str, tuple[date | None, str]] = {}
        for entry in sorted(game.get("release_dates") or [], key=_region_rank):
            region = REGIONS.get(entry.get("release_region", 0))
            if entry.get("platform") != platform_id or region is None or region in result:
                continue
            released = _date(entry.get("date"))
            precision = PRECISIONS.get(entry.get("category", 0), "day") if released else "tba"
            result[region] = (released, precision)
        return result

    @staticmethod
    def _first_release(
        game: dict[str, Any], platform_id: Any
    ) -> tuple[str | None, date | None, str]:
        """Prefer the European release (that's where the shelf is; Europe itself before
        Australia), else the earliest.
        Announced-but-undated releases come back as "tba"."""
        dates = [d for d in game.get("release_dates") or [] if d.get("platform") == platform_id]
        if not dates:
            return None, None, "day"
        dates.sort(
            key=lambda d: (REGIONS.get(d.get("release_region", 0)) != "pal", *_region_rank(d))
        )
        best = dates[0]
        precision = PRECISIONS.get(best.get("category", 0), "day")
        released = _date(best.get("date"))
        if released is None:
            precision = "tba"
        return REGIONS.get(best.get("release_region", 0)), released, precision
