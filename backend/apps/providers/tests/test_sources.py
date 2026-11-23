from typing import Any

import httpx
import pytest
from django.core.cache import cache

from apps.providers.services.integrations import save
from apps.providers.sources import ProviderError, metadata_source, metadata_sources
from apps.providers.sources.igdb import IGDBSource

from .fakes import IGDB_GAME, response, router


@pytest.fixture
def igdb(db: None, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    save("igdb", enabled=True, secrets={"client_id": "id", "client_secret": "secret"})
    cache.clear()
    bodies: list[str] = []

    def games(url: str, content: str = "", **kwargs: Any) -> httpx.Response:
        bodies.append(content)
        return response(json=[IGDB_GAME] if "26758" in content or "search" in content else [])

    monkeypatch.setattr(
        "httpx.post",
        router(
            {
                "https://id.twitch.tv": lambda *a, **k: response(
                    json={"access_token": "t", "expires_in": 100}
                ),
                "https://api.igdb.com": games,
            }
        ),
    )
    return bodies


def test_registry(db: None) -> None:
    assert metadata_sources() == []
    assert metadata_source("igdb") is None


def test_igdb_search_and_get(igdb: list[str]) -> None:
    source = IGDBSource()
    records = source.search('Mario "Odyssey"', "130")
    assert len(records) == 1
    record = records[0]
    assert record.title == "Super Mario Odyssey"
    assert record.region == "pal"  # the European date wins
    assert record.publisher == "Nintendo"
    assert record.developers == ["Nintendo EPD"]
    assert record.cover_url.endswith("/co1mxf.jpg")
    assert record.release_date is not None
    assert record.release_date.year == 2017
    assert 'search "Mario \\"Odyssey\\""' in igdb[0]
    assert "where platforms = (130)" in igdb[0]
    assert len(source.search("Mario")) == 2  # one record per platform
    assert source.get("26758", "130") == record
    assert source.get("1") is None


def test_igdb_credentials_not_in_url(db: None, monkeypatch: pytest.MonkeyPatch) -> None:
    save("igdb", enabled=True, secrets={"client_id": "id", "client_secret": "secret"})
    cache.clear()
    calls: list[tuple[str, dict[str, Any]]] = []

    def token(url: str, **kwargs: Any) -> httpx.Response:
        calls.append((url, kwargs))
        return response(json={"access_token": "t"})

    monkeypatch.setattr("httpx.post", router({"https://id.twitch.tv": token}))
    IGDBSource()._token()
    url, kwargs = calls[0]
    assert "secret" not in url
    assert "params" not in kwargs
    assert kwargs["data"]["client_secret"] == "secret"


def test_igdb_errors(db: None, monkeypatch: pytest.MonkeyPatch) -> None:
    save("igdb", enabled=True, secrets={"client_id": "id", "client_secret": "secret"})
    cache.clear()
    monkeypatch.setattr("httpx.post", router({}))
    with pytest.raises(ProviderError):
        IGDBSource().search("x")
    cache.set("providers:igdb:token:id", "stale")
    monkeypatch.setattr(
        "httpx.post", router({"https://api.igdb.com": lambda *a, **k: response(401, json={})})
    )
    with pytest.raises(ProviderError):
        IGDBSource().search("x")
    assert cache.get("providers:igdb:token:id") is None
    cache.set("providers:igdb:token:id", "t")
    monkeypatch.setattr(
        "httpx.post", router({"https://api.igdb.com": lambda *a, **k: response(json={"x": 1})})
    )
    with pytest.raises(ProviderError):
        IGDBSource().search("x")


def test_igdb_precision_and_regions(igdb: list[str]) -> None:
    game = {
        "id": 2,
        "name": "Soon",
        "platforms": [{"id": 130, "name": "Nintendo Switch"}],
        "release_dates": [
            {"platform": 130, "date": 4102444800, "release_region": 1, "category": 5},
            {"platform": 130, "release_region": 5, "category": 7},
            {"platform": 130, "date": 4102444800, "release_region": 1, "category": 0},
        ],
    }
    record = IGDBSource()._records(game, None)[0]
    assert record.release_precision == "quarter"
    assert record.regional_dates["jp"] == (None, "tba")
    assert record.regional_dates["pal"][1] == "quarter"
    only_tba = {**game, "release_dates": [{"platform": 130, "release_region": 2, "category": 7}]}
    tba = IGDBSource()._records(only_tba, None)[0]
    assert (tba.release_precision, tba.release_date, tba.region) == ("tba", None, "na")


def test_igdb_record_without_platforms(igdb: list[str]) -> None:
    game = {"id": 1, "name": "Mystery", "release_dates": [{"platform": None, "date": "x"}]}
    records = IGDBSource()._records(game, None)
    assert records[0].platform_external_id is None
    assert records[0].release_date is None


def test_igdb_europe_wins_over_australia(db: None) -> None:
    """Australia (region 3) often gets PAL games months before Europe (region 1): the shelf
    is European, so PAL is Europe's date (Professor Layton: AU April, EU November 2008)."""
    game = {
        "id": 1397,
        "name": "Professor Layton and the Curious Village",
        "platforms": [{"id": 20, "name": "Nintendo DS"}],
        "release_dates": [
            {"platform": 20, "date": 1171497600, "release_region": 5},  # JP 2007-02-15
            {"platform": 20, "date": 1207785600, "release_region": 3},  # AU 2008-04-10
            {"platform": 20, "date": 1226016000, "release_region": 1},  # EU 2008-11-07
        ],
    }
    record = IGDBSource()._records(game, None)[0]
    assert record.region == "pal"
    assert record.release_date
    assert record.release_date.isoformat() == "2008-11-07"
    assert record.regional_dates["pal"][0].isoformat() == "2008-11-07"  # type: ignore[union-attr]
    assert record.regional_dates["jp"][0].isoformat() == "2007-02-15"  # type: ignore[union-attr]
