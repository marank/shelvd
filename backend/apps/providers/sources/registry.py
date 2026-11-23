"""Which sources are active, in the order they are asked."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from .base import CoverSource, DescriptionSource, FactSource, MetadataSource
from .hltb import HLTBSource
from .igdb import IGDBSource
from .opencritic import OpenCriticSource
from .screenscraper import ScreenScraperSource
from .thegamesdb import TheGamesDBSource
from .wikipedia import WikipediaSource


class Testable(Protocol):
    def test(self) -> str: ...


def metadata_sources(catalog: bool = False) -> list[MetadataSource]:
    """Active metadata sources; with `catalog`, only those that can add games."""
    sources: tuple[MetadataSource, ...] = (IGDBSource(), WikipediaSource())
    return [s for s in sources if s.enabled() and (s.catalog or not catalog)]


def metadata_source(name: str, catalog: bool = False) -> MetadataSource | None:
    return next((s for s in metadata_sources(catalog) if s.name == name), None)


def description_source(name: str) -> DescriptionSource | None:
    """A source that describes companies (and series), if it's switched on."""
    sources: dict[str, Callable[[], DescriptionSource]] = {
        "wikipedia": WikipediaSource,
        "igdb": IGDBSource,
    }
    source = sources[name]() if name in sources else None
    return source if source is not None and source.enabled() else None


def fact_source(name: str) -> FactSource | None:
    """The facts source of that name, if it's switched on and set up."""
    sources: dict[str, type[HLTBSource] | type[OpenCriticSource]] = {
        "hltb": HLTBSource,
        "opencritic": OpenCriticSource,
    }
    source = sources[name]() if name in sources else None
    return source if source is not None and source.enabled() else None


def cover_sources() -> list[CoverSource]:
    return [s for s in (TheGamesDBSource(), ScreenScraperSource()) if s.enabled()]


# Sources of add-ons' integrations (see backend/addons), for their "Test" button.
EXTRA_TESTABLE: dict[str, Callable[[], Testable]] = {}


def register_testable(key: str, factory: Callable[[], Testable]) -> None:
    EXTRA_TESTABLE[key] = factory


def testable(key: str) -> Testable:
    """Any integration's source, switched on or not (to test its settings)."""
    sources: dict[str, Callable[[], Testable]] = {
        "igdb": IGDBSource,
        "hltb": HLTBSource,
        "opencritic": OpenCriticSource,
        "thegamesdb": TheGamesDBSource,
        "screenscraper": ScreenScraperSource,
        "wikipedia": WikipediaSource,
        **EXTRA_TESTABLE,
    }
    return sources[key]()
