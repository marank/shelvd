"""The interface every external source implements, and the records they return.

Sources never write to the database; services/ turns records into catalog rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol


class ProviderError(Exception):
    """A source could not be reached or answered with something unusable."""


class AuthExpiredError(ProviderError):
    """A person's stored token no longer works; they have to link the account again."""


@dataclass(frozen=True)
class GameRecord:
    """One game on one platform, normalized from a metadata source."""

    provider: str
    external_id: str
    title: str
    platform_external_id: str | None = None
    platform_name: str = ""
    region: str | None = None
    release_date: date | None = None
    release_precision: str = "day"  # catalog.DatePrecision value
    # Every region's (date, precision) for this platform, e.g. {"pal": (…, "day")}.
    regional_dates: dict[str, tuple[date | None, str]] = field(default_factory=dict)
    first_release_date: date | None = None
    publisher: str = ""
    developers: list[str] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)
    summary: str = ""
    cover_url: str = ""
    # The game's page at the source.
    url: str = ""
    # Every series it belongs to ("Super Mario", "… Ocarina of Time") and the brands above
    # them ("Mario").
    series: list[str] = field(default_factory=list)
    franchises: list[str] = field(default_factory=list)
    game_modes: list[str] = field(default_factory=list)  # "Single player", "Co-operative" …
    perspectives: list[str] = field(default_factory=list)  # "Third person" …
    # Language → what it covers: {"German": ["audio", "subtitles", "interface"]}.
    languages: dict[str, list[str]] = field(default_factory=dict)
    # Most players on this platform, side by side and online.
    players_offline: int | None = None
    players_online: int | None = None
    # How long it takes, in hours: {"main": 12.5, "extra": 20.0, "complete": 31.0}.
    play_times: dict[str, float] = field(default_factory=dict)


# What a metadata source can fill in when matching (see MetadataSource.fields).
METADATA_FIELDS = frozenset(
    {
        "title",
        "summary",
        "first_release_date",
        "genres",
        "developers",
        "release_date",
        "publisher",
        "cover",
    }
)


class GetFromAll:
    """`get` for a source whose `get_all` already does the work: the first record, if any."""

    def get_all(
        self, external_id: str, platform_external_id: str | None = None, language: str = "en"
    ) -> list[GameRecord]:
        raise NotImplementedError

    def get(
        self, external_id: str, platform_external_id: str | None = None, language: str = "en"
    ) -> GameRecord | None:
        records = self.get_all(external_id, platform_external_id, language)
        return records[0] if records else None


class MetadataSource(Protocol):
    """A source of game data. `language` ("de", "en" …) asks for titles, genres and texts in
    that language where the source has them; it falls back to its own (mostly English).

    `catalog` sources know a game per platform and can add it to the catalog (scan,
    search); the others only fill in fields of games we already have, when matching.
    `fields` says which of METADATA_FIELDS it can propose."""

    name: str
    catalog: bool
    fields: frozenset[str]

    def enabled(self) -> bool: ...

    def search(
        self, query: str, platform_external_id: str | None = None, language: str = "en"
    ) -> list[GameRecord]:
        """One record per (game, platform) pair, best matches first."""
        ...

    def get(
        self, external_id: str, platform_external_id: str | None = None, language: str = "en"
    ) -> GameRecord | None: ...

    def get_all(
        self, external_id: str, platform_external_id: str | None = None, language: str = "en"
    ) -> list[GameRecord]:
        """The game on every platform the source knows (or just that one)."""
        ...

    def test(self) -> str:
        """Check the connection; returns a short message or raises ProviderError."""
        ...


@dataclass(frozen=True)
class EntryRef:
    """Another encyclopedia entry (a parent company …): its id and names to find it by."""

    external_id: str
    names: tuple[str, ...]


@dataclass(frozen=True)
class CompanyFacts:
    """What an encyclopedia knows about a company; empty / None: unknown."""

    founded: int | None = None
    dissolved: int | None = None
    country: str = ""  # ISO 3166-1 alpha-2
    headquarters: str = ""
    website: str = ""
    parent: EntryRef | None = None
    subsidiaries: tuple[EntryRef, ...] = ()


@dataclass(frozen=True)
class PlatformFacts:
    """What an encyclopedia knows about a platform; empty / None: unknown."""

    short_name: str = ""
    released: int | None = None  # year
    discontinued: int | None = None  # year
    generation: int | None = None
    manufacturer: EntryRef | None = None
    predecessors: tuple[EntryRef, ...] = ()
    successors: tuple[EntryRef, ...] = ()


@dataclass(frozen=True)
class ImageOption:
    """A picture an entry offers: a logo (an older one …), a small logo ("icon") or a
    photo ("photo"), and its name."""

    url: str
    label: str = ""
    kind: str = "logo"


@dataclass(frozen=True)
class DescriptionRecord:
    """An encyclopedia entry for a company or series: what it is (`label`, e.g. "Japanese
    video game company"), its text in the asked language or else another (`language`; ""
    and no text for a company entry without any article – it still has facts), its logo
    (`image_url`, fetched only by the source's `image`) and whether it surely is the
    searched one (`confident`: the right kind of thing, with exactly that name).

    Only `description` (one entry) fills `texts` – every language's –, `images` (every
    picture to choose from, `image_url` first) and `company` or `platform`."""

    source: str
    external_id: str
    title: str
    label: str = ""
    text: str = ""
    language: str = ""
    image_url: str = ""
    confident: bool = False
    texts: dict[str, str] = field(default_factory=dict)
    images: tuple[ImageOption, ...] = ()
    company: CompanyFacts | None = None
    platform: PlatformFacts | None = None
    franchise: EntryRef | None = None  # a series' franchise


class DescriptionSource(Protocol):
    """Describes companies, series and platforms (`kind` "companies", "series",
    "platforms") in a language."""

    name: str

    def enabled(self) -> bool: ...

    def describe(self, query: str, kind: str, language: str = "en") -> list[DescriptionRecord]:
        """Candidates with their texts, the likeliest kind of thing first."""
        ...

    def description(
        self, external_id: str, language: str = "en", kind: str = ""
    ) -> DescriptionRecord | None:
        """The entry with every language's text (and a company's or platform's facts)."""
        ...

    def image(self, url: str) -> bytes:
        """A record's `image_url` or one of its `images` (only from the source's own
        hosts); raises ProviderError."""
        ...


@dataclass(frozen=True)
class FactRecord:
    """What a facts source knows about one game: play times, critic scores …

    `values` holds the source's numbers (e.g. {"main": 12.5, "extra": 20.0}); `url` links
    to the game on the source's site."""

    source: str
    external_id: str
    title: str
    url: str = ""
    year: int | None = None
    platforms: str = ""
    values: dict[str, float] = field(default_factory=dict)


class FactSource(Protocol):
    name: str

    def enabled(self) -> bool: ...

    def search(self, title: str) -> list[FactRecord]:
        """Candidates for a title, best matches first; values may be filled in already."""
        ...

    def get(self, external_id: str) -> FactRecord | None: ...

    def test(self) -> str:
        """Check the connection; returns a short message or raises ProviderError."""
        ...


@dataclass(frozen=True)
class CoverRecord:
    """One cover image a covers source offers for a game (front box art)."""

    source: str
    url: str
    title: str
    region: str = ""
    platform: str = ""
    width: int | None = None
    height: int | None = None


class CoverSource(Protocol):
    name: str
    # Hosts its image URLs may point to; nothing else is ever fetched.
    hosts: tuple[str, ...]
    # Quick and cheap enough to be asked while someone waits for a scanned game to be added.
    automatic: bool

    def enabled(self) -> bool: ...

    def covers(self, title: str, platform_slug: str = "") -> list[CoverRecord]: ...

    def test(self) -> str: ...
