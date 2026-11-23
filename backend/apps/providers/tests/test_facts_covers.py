# ruff: noqa: E501
import io
import json
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import httpx
import pytest
from django.core.cache import cache
from django.utils import timezone, translation
from PIL import Image

from apps.accounts.models import User
from apps.catalog.models import Platform, Release, Work, WorkFact
from apps.collection.models import Item, Library
from apps.providers.services import covers, facts
from apps.providers.services.importer import import_record
from apps.providers.services.integrations import config, encrypt, save
from apps.providers.sources import GameRecord, ProviderError
from apps.providers.sources.hltb import HLTBSource
from apps.providers.sources.opencritic import OpenCriticSource
from apps.providers.sources.screenscraper import ScreenScraperSource
from apps.providers.sources.thegamesdb import TheGamesDBSource

from .fakes import response, router

GAME = {"game_id": 101, "game_name": "Super Mario Odyssey", "comp_main": 45000,
        "comp_plus": 72000, "comp_100": 0, "release_world": 2017, "profile_platform": "Switch"}  # fmt: skip
PAGE = (
    '<script id="__NEXT_DATA__" type="application/json">'
    + json.dumps({"props": {"pageProps": {"game": {"data": {"game": [GAME]}}}}})
    + "</script>"
)


@pytest.fixture
def hltb(db: None, monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    cache.clear()
    save("hltb", enabled=True)
    posts: list[dict[str, Any]] = []
    hltb_routes(monkeypatch, posts)
    return posts


def hltb_routes(monkeypatch: pytest.MonkeyPatch, posts: list[dict[str, Any]] | None = None) -> None:
    cache.clear()

    def page(url: str, **kwargs: Any) -> httpx.Response:
        if "/api/search/site/init" in url:
            return response(json={"token": "tok"})
        return response(content=PAGE.encode(), ctype="text/html")

    def search(url: str, **kwargs: Any) -> httpx.Response:
        if posts is not None:
            posts.append({"url": url, **kwargs})
        return response(json={"data": [GAME, {"game_id": 7, "game_name": "Mario Kart"}]})

    monkeypatch.setattr("httpx.get", router({"https://howlongtobeat.com": page}))
    monkeypatch.setattr("httpx.post", router({"https://howlongtobeat.com/api/search/site": search}))


@pytest.fixture
def mario(make_release: Callable[..., Release], switch: Platform) -> Release:
    return make_release("Super Mario Odyssey", switch)


def test_hltb_search_and_page(hltb: list[dict[str, Any]]) -> None:
    source = HLTBSource()
    found = source.search("Super Mario Odyssey")
    assert found[0].values == {"main": 12.5, "extra": 20.0}  # 0 seconds = unknown
    assert (found[0].year, found[0].platforms, found[0].url) == (
        2017,
        "Switch",
        "https://howlongtobeat.com/game/101",
    )
    assert hltb[0]["json"]["searchTerms"] == ["Super", "Mario", "Odyssey"]
    assert hltb[0]["headers"]["x-auth-token"] == "tok"
    assert source.get("101").title == "Super Mario Odyssey"  # type: ignore[union-attr]
    assert source.get("abc") is None
    assert source.test() == "2 Treffer für „Super Mario Odyssey“"


def test_hltb_token_and_site_changes(db: None, monkeypatch: pytest.MonkeyPatch) -> None:
    cache.clear()
    source = HLTBSource()
    tokens = iter(["old", "new"])
    monkeypatch.setattr(
        "httpx.get",
        router(
            {
                "https://howlongtobeat.com/api/search/site/init": lambda *a, **k: response(
                    json={"token": next(tokens)}
                )
            }
        ),
    )
    seen: list[str] = []

    def search(url: str, **kwargs: Any) -> httpx.Response:
        seen.append(kwargs["headers"]["x-auth-token"])
        return (
            response(403, json={})
            if kwargs["headers"]["x-auth-token"] == "old"
            else response(json={"data": [GAME]})
        )

    monkeypatch.setattr("httpx.post", router({"https://howlongtobeat.com/api/search/site": search}))
    # An expired token is replaced once; the new one is cached.
    assert [r.title for r in source.search("x")] == ["Super Mario Odyssey"]
    assert seen == ["old", "new"]
    assert cache.get("providers:hltb:token") == "new"
    # Still refused with a fresh token: an error.
    monkeypatch.setattr(
        "httpx.post", router({"https://howlongtobeat.com": lambda *a, **k: response(403, json={})})
    )
    monkeypatch.setattr(
        "httpx.get",
        router({"https://howlongtobeat.com": lambda *a, **k: response(json={"token": "t"})}),
    )
    with pytest.raises(ProviderError):
        source.search("x")
    # No token, or no init at all.
    cache.clear()
    monkeypatch.setattr(
        "httpx.get", router({"https://howlongtobeat.com": lambda *a, **k: response(json={})})
    )
    with pytest.raises(ProviderError, match="no search token"):
        source.search("x")
    monkeypatch.setattr("httpx.get", router({}))
    with pytest.raises(ProviderError, match="init failed"):
        source.search("x")
    # Unexpected answers and pages without data.
    cache.set("providers:hltb:token", "t")
    monkeypatch.setattr(
        "httpx.post", router({"https://howlongtobeat.com": lambda *a, **k: response(json=[1])})
    )
    with pytest.raises(ProviderError, match="unexpected"):
        source.search("x")
    monkeypatch.setattr(
        "httpx.get",
        router({"https://howlongtobeat.com": lambda *a, **k: response(content=b"<html>")}),
    )
    assert source.get("5") is None


def test_refresh_cache_and_staleness(hltb: list[dict[str, Any]], mario: Release, api: Any) -> None:
    work = mario.work
    fact = facts.refresh(work, "hltb")
    assert fact is not None
    assert fact.values == {"main": 12.5, "extra": 20.0}
    assert len(hltb) == 1
    assert facts.refresh(work, "hltb") == fact
    assert len(hltb) == 1
    # Facts appear on the release (play time per game).
    body = api.get(f"/catalog/releases/{mario.pk}").json()
    assert body["facts"]["hltb"]["values"]["main"] == 12.5
    # Stale after max age: opening the game refreshes it.
    WorkFact.objects.update(fetched_at=timezone.now() - timedelta(days=31))
    assert api.post(f"/catalog/works/{work.pk}/facts/refresh").json() == {"refreshed": True}
    assert len(hltb) == 2
    assert api.post(f"/catalog/works/{work.pk}/facts/refresh").json() == {"refreshed": False}
    assert api.post(f"/catalog/works/{work.pk}/facts/refresh?force=true").json() == {
        "refreshed": True
    }
    # Sorting and filtering by play time (cached values, no requests).
    from apps.collection.models import Item, Library

    library = Library.objects.create(owner=User.objects.get(username="alice"), name="L")
    Item.objects.create(library=library, release=mario)
    Item.objects.create(library=library, release=Release.objects.create(
        work=Work.objects.create(title="Short"), platform=mario.platform, region="pal"))  # fmt: skip
    path = f"/libraries/{library.pk}/items"

    def titles(**query: str) -> list[str]:
        return [i["title"] for i in api.get(path, query).json()["items"]]

    assert titles(sort="-game.time_main") == ["Super Mario Odyssey", "Short"]
    assert titles(where="game.time_main>=10") == ["Super Mario Odyssey"]
    assert titles(where="game.time_main!?") == ["Short"]


def test_no_match_failures_and_pinning(
    hltb: list[dict[str, Any]],
    make_release: Callable[..., Release],
    switch: Platform,
    api: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    work = make_release("Totally Unknown Game", switch).work
    fact = facts.refresh(work, "hltb")
    assert fact is not None
    assert fact.status == "missing"
    assert fact.values == {}
    # A failing source keeps the cache and records the error.
    monkeypatch.setattr("httpx.post", router({}))
    assert facts.refresh(work, "hltb", force=True) == fact
    assert "HowLongToBeat" in config("hltb").row.last_error  # type: ignore[union-attr]
    candidates = api.get(f"/catalog/works/{work.pk}/facts/hltb/candidates", {"q": "mario"})
    assert candidates.status_code == 502
    monkeypatch.undo()
    # (re-install the HLTB fakes undone above)
    hltb_routes(monkeypatch)
    listed = api.get(f"/catalog/works/{work.pk}/facts/hltb/candidates", {"q": "mario"}).json()
    assert [c["external_id"] for c in listed] == ["101", "7"]
    pinned = api.put(f"/catalog/works/{work.pk}/facts/hltb", {"external_id": "101"}).json()
    assert (pinned["pinned"], pinned["title"]) == (True, "Super Mario Odyssey")
    # Pinned: refreshing reads that entry again, it doesn't search.
    WorkFact.objects.update(fetched_at=None)
    assert facts.refresh(work, "hltb").title == "Super Mario Odyssey"  # type: ignore[union-attr]
    assert api.put(f"/catalog/works/{work.pk}/facts/hltb", {"external_id": "x"}).status_code == 404
    assert api.delete(f"/catalog/works/{work.pk}/facts/hltb").status_code == 204
    assert not WorkFact.objects.filter(work=work).exists()
    save("hltb", enabled=False)
    assert api.get(f"/catalog/works/{work.pk}/facts/hltb/candidates").status_code == 400
    assert (
        api.put(f"/catalog/works/{work.pk}/facts/hltb", {"external_id": "101"}).status_code == 400
    )


def test_best_match() -> None:
    from apps.providers.sources.base import FactRecord

    def r(title: str) -> FactRecord:
        return FactRecord(source="x", external_id=title, title=title)

    assert facts.best_match("Dave the Diver", [r("Dave The Diver: Complete Edition")]) is not None
    assert facts.best_match("Zelda", [r("Mario")]) is None
    best = facts.best_match("Metroid Prime 4", [r("Metroid Prime 3"), r("Metroid Prime 4")])
    assert best is not None
    assert best.title == "Metroid Prime 4"
    kawashima = r("Dr Kawashima's Brain Training for Nintendo Switch")
    assert facts.best_match("Dr Kawashima's Brain Training", [kawashima]) is kawashima
    assert facts.best_match("Metroid Prime", [r("Metroid Prime 3")], exact=True) is None
    # Pairs under one entry, accents folded.
    pair = r("Pokémon Omega Ruby and Alpha Sapphire")
    assert facts.best_match("Pokemon Alpha Sapphire", [pair], exact=True) is pair
    assert facts.best_match("Pokémon Y", [r("Pokémon Yellow"), xy := r("Pokémon X and Y")]) is xy
    assert facts.title_forms("Ratchet & Clank") == ["Ratchet & Clank"]
    assert (
        facts.best_match("Pokémon White 2", [r("Pokémon Blaze Black 2 and Volt White 2")]) is None
    )


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Super Mario Odyssey", [("Super Mario Odyssey", False)]),
        ("As Dusk Falls: Special Edition", [("As Dusk Falls: Special Edition", False), ("As Dusk Falls", False)]),
        ("Darksiders Warmastered Edition", [("Darksiders Warmastered Edition", False), ("Darksiders Warmastered", False), ("Darksiders", False)]),
        ("ATOMIK: RunGunJumpGun", [("ATOMIK: RunGunJumpGun", False), ("ATOMIK RunGunJumpGun", False), ("RunGunJumpGun", True)]),
        ("Agatha Christie - Murder on the Orient Express", [("Agatha Christie - Murder on the Orient Express", False), ("Agatha Christie Murder on the Orient Express", False), ("Murder on the Orient Express", True)]),
        ("Pokémon Black Version 2", [("Pokémon Black Version 2", False), ("Pokémon Black 2", False)]),
        ("Zelda: Botw", [("Zelda: Botw", False), ("Zelda Botw", False), ("Botw", True)]),
        ("Zelda: II", [("Zelda: II", False), ("Zelda II", False)]),
    ],
)  # fmt: skip
def test_fact_titles(title: str, expected: list[tuple[str, bool]]) -> None:
    assert facts.fact_titles(title) == expected


def test_find_tries_shorter_titles() -> None:
    from apps.providers.sources.base import FactRecord

    asked: list[str] = []

    class Source:
        def search(self, query: str) -> list[FactRecord]:
            asked.append(query)
            names = {
                "Darksiders": ["Darksiders", "Darksiders II"],
                "RunGunJumpGun": ["RunGunJumpGun"],
            }
            return [FactRecord(source="x", external_id=n, title=n) for n in names.get(query, [])]

    found = facts.find(Source(), "Darksiders Warmastered Edition")  # type: ignore[arg-type]
    assert found is not None
    assert found.title == "Darksiders"
    assert asked == ["Darksiders Warmastered Edition", "Darksiders Warmastered", "Darksiders"]
    found = facts.find(Source(), "ATOMIK: RunGunJumpGun")  # type: ignore[arg-type]
    assert found is not None
    assert found.title == "RunGunJumpGun"
    assert facts.find(Source(), "Nothing: Here") is None  # type: ignore[arg-type]


def test_figures_have_no_facts(
    hltb: list[dict[str, Any]], make_release: Callable[..., Release], switch: Platform
) -> None:
    figure = make_release("Super Mario Odyssey", switch).work
    figure.media_type = "toy"
    figure.save()
    assert facts.refresh(figure, "hltb") is None
    assert facts.refresh_batch("hltb", 5) == 0
    assert not hltb
    assert not WorkFact.objects.exists()


def test_refresh_batch(
    hltb: list[dict[str, Any]], make_release: Callable[..., Release], switch: Platform
) -> None:
    make_release("Super Mario Odyssey", switch)
    make_release("Unknown", switch)
    assert facts.refresh_batch("hltb", 5) == 2
    assert facts.refresh_batch("hltb", 5) == 0  # all fresh
    save("hltb", enabled=False)
    assert facts.refresh_batch("hltb", 5) == 0


def test_opencritic(db: None, monkeypatch: pytest.MonkeyPatch, mario: Release) -> None:
    save("opencritic", enabled=True, secrets={"rapidapi_key": "key"})
    seen: list[dict[str, Any]] = []

    def handler(url: str, **kwargs: Any) -> httpx.Response:
        seen.append(kwargs)
        if url.endswith("/game/search"):
            return response(json=[{"id": 4504, "name": "Super Mario Odyssey"}, {"name": "no id"}])
        if url.endswith("/game/4504"):
            return response(json={"id": 4504, "name": "Super Mario Odyssey", "topCriticScore": 97.2,
                                  "percentRecommended": 99, "firstReleaseDate": "2017-10-27"})  # fmt: skip
        return response(404, json={})

    monkeypatch.setattr("httpx.get", router({"https://opencritic-api.p.rapidapi.com": handler}))
    fact = facts.refresh(mario.work, "opencritic")
    assert fact is not None
    assert fact.values == {"score": 97.2, "recommended": 99.0}
    assert fact.url == "https://opencritic.com/game/4504/super-mario-odyssey"
    assert seen[0]["headers"]["X-RapidAPI-Key"] == "key"
    assert OpenCriticSource().get("1") is None
    assert OpenCriticSource().test() == "1 Treffer für „Zelda“"
    monkeypatch.setattr(
        "httpx.get",
        router({"https://opencritic-api.p.rapidapi.com": lambda *a, **k: response(json={"x": 1})}),
    )
    with pytest.raises(ProviderError):
        OpenCriticSource().search("x")


TGDB = {
    "data": {"games": [{"id": 1, "game_title": "Super Mario Odyssey", "platform": 4971, "region_id": 6},
                       {"id": 2, "game_title": "Super Mario Odyssey", "platform": 1}]},
    "include": {"boxart": {"base_url": {"original": "https://cdn.thegamesdb.net/images/original/"},
                           "data": {"1": [{"side": "front", "filename": "boxart/front/1.jpg", "resolution": "600x980"},
                                          {"side": "back", "filename": "boxart/back/1.jpg"}],
                                    "2": [{"side": "front", "filename": "boxart/front/2.jpg"}]}}},
}  # fmt: skip
SS = {"response": {"jeux": [{"id": "9", "noms": [{"text": "Super Mario Odyssey"}], "systeme": {"id": "225"},
      "medias": [{"type": "box-2D", "region": "eu", "url": "https://neoclone.screenscraper.fr/api2/mediaJeu.php?devid=secret&media=box-2D(eu)"},
                 {"type": "ss", "url": "https://neoclone.screenscraper.fr/x"}]}, {"noms": []}],
      "ssuser": {"requeststoday": 3, "maxrequestsperday": 20000}}}  # fmt: skip
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@pytest.fixture
def cover_sources(db: None, monkeypatch: pytest.MonkeyPatch) -> None:
    save("thegamesdb", enabled=True, secrets={"api_key": "k"})
    save("screenscraper", enabled=True, options={"user": "me"},
         secrets={"dev_id": "d", "dev_password": "p", "password": "pw"})  # fmt: skip
    monkeypatch.setattr(
        "httpx.get",
        router({
            "https://api.thegamesdb.net": lambda *a, **k: response(json=TGDB),
            "https://api.screenscraper.fr": lambda *a, **k: response(json=SS),
            "https://cdn.thegamesdb.net": lambda *a, **k: response(content=PNG, ctype="image/png"),
            "https://neoclone.screenscraper.fr": lambda *a, **k: response(content=b"x", ctype="text/html"),
        }),
    )  # fmt: skip


def test_cover_sources(cover_sources: None) -> None:
    tgdb = TheGamesDBSource().covers("Super Mario Odyssey", "switch")
    assert [(c.platform, c.region, c.width) for c in tgdb] == [
        ("switch", "pal", 600),
        ("pc", "", None),
    ]
    ss = ScreenScraperSource().covers("Super Mario Odyssey", "switch")
    assert [(c.platform, c.region) for c in ss] == [("switch", "pal")]
    assert ScreenScraperSource().test() == "OK – heute 3 von 20000 Abfragen"


def test_cover_flow(cover_sources: None, mario: Release, api: Any) -> None:
    listed = api.get(f"/catalog/releases/{mario.pk}/cover-candidates").json()
    assert [c["source"] for c in listed] == ["thegamesdb", "thegamesdb", "screenscraper"]
    # Credentials never leave the server.
    assert "secret" not in json.dumps(listed)
    token = listed[0]["token"]
    preview = api.get("/catalog/cover-preview", {"token": token})
    assert (preview.status_code, preview["Content-Type"]) == (200, "image/png")
    # Not an image → refused; foreign hosts or tampered tokens → refused.
    assert api.get("/catalog/cover-preview", {"token": listed[2]["token"]}).status_code == 502
    evil = encrypt(json.dumps({"source": "thegamesdb", "url": "https://evil.example/x.png"}))
    assert api.get("/catalog/cover-preview", {"token": evil}).status_code == 400
    plain = encrypt(json.dumps({"source": "thegamesdb", "url": "http://cdn.thegamesdb.net/x.png"}))
    assert api.get("/catalog/cover-preview", {"token": plain}).status_code == 400
    assert api.get("/catalog/cover-preview", {"token": "garbage"}).status_code == 400
    applied = api.post(f"/catalog/releases/{mario.pk}/cover-from", {"token": token}).json()
    assert applied["cover_url"]
    assert applied["cover_source"] == "thegamesdb"


def tgdb_games(*games: tuple[int, str, int, int | None, str]) -> dict[str, Any]:
    """TheGamesDB's answer for (id, title, platform, region id, resolution) rows."""
    return {
        "data": {"games": [{"id": i, "game_title": t, "platform": p, "region_id": r} for i, t, p, r, _ in games]},
        "include": {"boxart": {"base_url": {"original": "https://cdn.thegamesdb.net/images/original/"},
                               "data": {str(g[0]): [{"side": "front", "filename": f"{g[0]}.jpg", "resolution": g[4]}] for g in games}}},
    }  # fmt: skip


def tgdb_routes(monkeypatch: pytest.MonkeyPatch, answer: dict[str, Any]) -> list[str]:
    """Answers TheGamesDB with `answer`; returns the list of image URLs fetched."""
    save("thegamesdb", enabled=True, secrets={"api_key": "k"})
    fetched: list[str] = []

    def image(url: str, **kwargs: Any) -> httpx.Response:
        fetched.append(url)
        return response(content=PNG, ctype="image/png")

    monkeypatch.setattr(
        "httpx.get",
        router({"https://api.thegamesdb.net": lambda *a, **k: response(json=answer),
                "https://cdn.thegamesdb.net": image}),
    )  # fmt: skip
    return fetched


@pytest.mark.parametrize(
    ("region", "expected"),
    [("pal", "3.jpg"), ("de", "3.jpg"), ("jp", "4.jpg"), ("kr", "3.jpg")],
)
def test_platform_cover_picks_game_platform_region(
    db: None,
    make_release: Callable[..., Release],
    switch: Platform,
    monkeypatch: pytest.MonkeyPatch,
    region: str,
    expected: str,
) -> None:
    release = make_release("Pokémon: Odyssey", switch, region=region)
    fetched = tgdb_routes(monkeypatch, tgdb_games(
        (1, "Pokemon Odyssey", 1, 6, "2000x3000"),  # other platform
        (2, "Pokemon Odyssey [Limited Edition]", 4971, 6, "2000x3000"),  # other edition
        (3, "Pokemon Odyssey", 4971, 6, "600x900"),
        (4, "POKÉMON ODYSSEY", 4971, 4, "600x900"),
        (5, "Pokemon Odyssey", 4971, 6, "100x150"),
        (6, "Pac-Man", 4971, 6, "2000x3000"),  # search noise
    ))  # fmt: skip
    assert covers.take_platform_cover(release) is True
    assert fetched[0].endswith(expected)
    assert release.cover_source == "thegamesdb"


def test_platform_cover_without_a_fit(mario: Release, monkeypatch: pytest.MonkeyPatch) -> None:
    fetched = tgdb_routes(monkeypatch, tgdb_games(
        (1, "Super Mario Odyssey", 1, 6, "600x900"),
        (2, "Super Mario Galaxy", 4971, 6, "600x900"),
    ))  # fmt: skip
    assert covers.take_platform_cover(mario) is False
    assert fetched == []
    assert not mario.cover


def test_platform_cover_asks_only_quick_sources(
    cover_sources: None, mario: Release, monkeypatch: pytest.MonkeyPatch
) -> None:
    save("thegamesdb", enabled=False, secrets={"api_key": "k"})
    # The fixture's ScreenScraper has a matching cover, but must not be asked.
    assert covers.take_platform_cover(mario) is False


def test_platform_cover_failures(mario: Release, monkeypatch: pytest.MonkeyPatch) -> None:
    save("thegamesdb", enabled=True, secrets={"api_key": "k"})
    monkeypatch.setattr("httpx.get", router({}))
    assert covers.take_platform_cover(mario) is False
    assert "TheGamesDB" in config("thegamesdb").row.last_error  # type: ignore[union-attr]

    answer = tgdb_games((1, "Super Mario Odyssey", 4971, 6, "600x900"))
    monkeypatch.setattr(
        "httpx.get",
        router({"https://api.thegamesdb.net": lambda *a, **k: response(json=answer),
                "https://cdn.thegamesdb.net": lambda *a, **k: response(content=b"x", ctype="text/html")}),
    )  # fmt: skip
    assert covers.take_platform_cover(mario) is False
    assert not mario.cover


def test_platform_cover_deadline(mario: Release, monkeypatch: pytest.MonkeyPatch) -> None:
    fetched = tgdb_routes(monkeypatch, tgdb_games((1, "Super Mario Odyssey", 4971, 6, "600x900")))
    monkeypatch.setattr(covers, "AUTOMATIC_DEADLINE", -1.0)
    assert covers.take_platform_cover(mario) is False
    assert fetched == []


def test_import_splits_covers(db: None, switch: Platform, monkeypatch: pytest.MonkeyPatch) -> None:
    igdb_cover = lambda *a, **k: response(content=PNG, ctype="image/png")  # noqa: E731
    answer = tgdb_games((1, "Super Mario Odyssey", 4971, 6, "600x900"))
    monkeypatch.setattr(
        "httpx.get",
        router({"https://api.thegamesdb.net": lambda *a, **k: response(json=answer),
                "https://cdn.thegamesdb.net": igdb_cover,
                "https://images.igdb.com": igdb_cover}),
    )  # fmt: skip
    save("thegamesdb", enabled=True, secrets={"api_key": "k"})
    record = GameRecord(provider="igdb", external_id="7", title="Super Mario Odyssey",
                        cover_url="https://images.igdb.com/x.jpg")  # fmt: skip
    release = import_record(record, switch, "pal")
    assert release.cover_source == "thegamesdb"
    assert release.cover
    assert release.work.cover
    assert release.work.cover.name != release.cover.name

    # No box art for this platform: the release has none and shows the game's.
    other = GameRecord(provider="igdb", external_id="8", title="Unknown Game",
                       cover_url="https://images.igdb.com/x.jpg")  # fmt: skip
    release = import_record(other, switch, "pal")
    assert not release.cover
    assert release.cover_source == ""
    assert release.cover_url == release.work.cover.url


def test_cover_sources_failing(db: None, mario: Release, monkeypatch: pytest.MonkeyPatch) -> None:
    save("thegamesdb", enabled=True, secrets={"api_key": "k"})
    monkeypatch.setattr("httpx.get", router({}))
    assert covers.candidates(mario) == []
    assert "TheGamesDB" in config("thegamesdb").row.last_error  # type: ignore[union-attr]
    with pytest.raises(ProviderError):
        TheGamesDBSource().test()
    monkeypatch.setattr(
        "httpx.get", router({"https://api.thegamesdb.net": lambda *a, **k: response(json=[1])})
    )
    with pytest.raises(ProviderError):
        TheGamesDBSource().covers("x")
    # An HTTP error names the URL, and that carries the key: only the status is kept.
    save("thegamesdb", enabled=True, secrets={"api_key": "secret-key"})
    monkeypatch.setattr(
        "httpx.get", router({"https://api.thegamesdb.net": lambda *a, **k: response(status=403)})
    )
    with pytest.raises(ProviderError, match=r"\(HTTP 403\)") as tgdb_error:
        TheGamesDBSource().covers("x")
    assert "secret-key" not in str(tgdb_error.value)
    save(
        "screenscraper",
        enabled=True,
        options={"user": "me"},
        secrets={"dev_id": "d", "dev_password": "p", "password": "pw"},
    )
    monkeypatch.setattr("httpx.get", router({}))
    with pytest.raises(ProviderError) as error:
        ScreenScraperSource().covers("x")
    assert "pw" not in str(error.value)
    monkeypatch.setattr(
        "httpx.get",
        router({"https://api.screenscraper.fr": lambda *a, **k: response(json={"x": 1})}),
    )
    with pytest.raises(ProviderError):
        ScreenScraperSource().covers("x")

    def slow(url: str, **kwargs: Any) -> httpx.Response:
        assert kwargs["timeout"].read == 20.0  # longer than the other sources
        raise httpx.ReadTimeout("slow")

    monkeypatch.setattr("httpx.get", slow)
    with pytest.raises(ProviderError, match="ScreenScraper"):
        ScreenScraperSource().covers("x")


def test_screenscraper_without_developer_credentials(
    db: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A plain user account is enough to try: developer fields are left out when empty.
    save("screenscraper", enabled=True, options={"user": "me"}, secrets={"password": "pw"})
    sent: dict[str, Any] = {}

    def answer(url: str, *args: Any, params: dict[str, str], **kwargs: Any) -> Any:
        sent.update(params)
        return response(json=SS)

    monkeypatch.setattr("httpx.get", router({"https://api.screenscraper.fr": answer}))
    assert ScreenScraperSource().covers("Super Mario Odyssey")
    assert "devid" not in sent
    assert sent["ssid"] == "me"

    # ScreenScraper's plain-text errors become readable messages.
    for status, text, expected in (
        (200, "Erreur de login : Vérifier vos identifiants développeur !", "developer"),
        (403, "Erreur de login : Vérifier les identifiants utilisateurs !", "user name"),
        (500, "boom", "HTTP 500"),
    ):
        monkeypatch.setattr(
            "httpx.get",
            router({
                "https://api.screenscraper.fr": lambda *a, s=status, t=text, **k: response(
                    status=s, content=t.encode(), ctype="text/html"
                )
            }),
        )  # fmt: skip
        with translation.override("en"), pytest.raises(ProviderError, match=expected):
            ScreenScraperSource().test()


def test_cover_for_one_copy(
    cover_sources: None, mario: Release, library: Library, api: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A copy can take a source cover as its own, leaving the catalog's cover alone.
    buffer = io.BytesIO()
    Image.new("RGB", (4, 6), "red").save(buffer, "PNG")
    real_png = buffer.getvalue()
    item = Item.objects.create(library=library, release=mario)
    token = api.get(f"/catalog/releases/{mario.pk}/cover-candidates").json()[0]["token"]
    path = f"/libraries/{library.pk}/items/{item.pk}/cover-from"
    # Not a valid image → refused.
    assert api.post(path, {"token": token}).status_code == 400
    monkeypatch.setattr(
        "httpx.get",
        router({"https://cdn.thegamesdb.net": lambda *a, **k: response(
            content=real_png, ctype="image/png"
        )}),
    )  # fmt: skip
    body = api.post(path, {"token": token}).json()
    assert body["has_cover_override"] is True
    assert body["cover_url"].startswith("/media/item-covers/")
    mario.refresh_from_db()
    assert not mario.cover
    # Viewers may not change a copy.
    other = Library.objects.create(name="Other", owner=User.objects.create(username="x"))
    foreign = Item.objects.create(library=other, release=mario)
    assert (
        api.post(
            f"/libraries/{other.pk}/items/{foreign.pk}/cover-from", {"token": token}
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("As Dusk Falls: Special Edition", ["As Dusk Falls: Special Edition", "As Dusk Falls"]),
        ("Bloodborne Game of the Year Edition", ["Bloodborne Game of the Year Edition", "Bloodborne"]),
        ("The Last of Us Remastered", ["The Last of Us Remastered", "The Last of Us"]),
        ("Zelda (Limited Edition)", ["Zelda (Limited Edition)", "Zelda"]),
        ("Halo: The Master Chief Collection", ["Halo: The Master Chief Collection"]),
        ("Persona 5 Royal", ["Persona 5 Royal", "Persona 5"]),
    ],
)  # fmt: skip
def test_search_titles(title: str, expected: list[str]) -> None:
    assert covers.search_titles(title) == expected


def test_cover_search_falls_back_and_takes_a_query(
    db: None, mario: Release, api: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    save("thegamesdb", enabled=True, secrets={"api_key": "k"})
    mario.work.title = "Super Mario Odyssey: Special Edition"
    mario.work.save()
    asked: list[str] = []

    def answer(url: str, *args: Any, params: dict[str, str], **kwargs: Any) -> Any:
        asked.append(params["name"])
        return response(json=TGDB if params["name"] == "Super Mario Odyssey" else {"data": {}})

    monkeypatch.setattr("httpx.get", router({"https://api.thegamesdb.net": answer}))
    path = f"/catalog/releases/{mario.pk}/cover-candidates"
    assert len(api.get(path).json()) == 2
    assert asked == ["Super Mario Odyssey: Special Edition", "Super Mario Odyssey"]
    asked.clear()
    assert api.get(path, {"q": "Something else"}).json() == []
    assert asked == ["Something else"]


def test_cover_search_stops_at_the_deadline(
    mario: Release, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Slow sources don't add up past gunicorn's timeout: after the deadline no further
    title form or source is asked, and what was found so far is returned."""
    from apps.providers.sources.base import CoverRecord

    mario.work.title = "Super Mario Odyssey: Special Edition"
    clock = [0.0]
    asked: list[tuple[str, str]] = []

    class Slow:
        hosts = ("example.invalid",)

        def __init__(self, name: str, found: bool) -> None:
            self.name, self.found = name, found

        def covers(self, title: str, platform_slug: str = "") -> list[CoverRecord]:
            asked.append((self.name, title))
            clock[0] += covers.DEADLINE + 1
            return [CoverRecord(self.name, "https://example.invalid/c.jpg", title)] * self.found

    monkeypatch.setattr(covers, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        covers, "cover_sources", lambda: [Slow("thegamesdb", False), Slow("screenscraper", True)]
    )
    assert covers.candidates(mario) == []
    assert asked == [("thegamesdb", "Super Mario Odyssey: Special Edition")]

    asked.clear()
    monkeypatch.setattr(
        covers, "cover_sources", lambda: [Slow("thegamesdb", True), Slow("screenscraper", True)]
    )
    found = covers.candidates(mario)
    assert [c.record.source for c in found] == ["thegamesdb"]
    assert asked == [("thegamesdb", "Super Mario Odyssey: Special Edition")]
