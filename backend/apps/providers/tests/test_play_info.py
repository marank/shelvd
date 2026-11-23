"""How a game is played, from IGDB: series, modes, perspectives, players, languages and
its time to beat – taken on import, offered when matching."""

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from django.core.cache import cache

from apps.catalog.models import Platform, Release, WorkFact
from apps.providers.services import metadata
from apps.providers.services.importer import import_record
from apps.providers.services.integrations import save
from apps.providers.sources.igdb import IGDBSource

from .fakes import IGDB_GAME, response, router

GAME = {
    **IGDB_GAME,
    "url": "https://www.igdb.com/games/super-mario-odyssey",
    "franchises": [{"name": "Mario"}],
    "collections": [{"name": "Super Mario 3D"}],
    "game_modes": [{"name": "Single player"}, {"name": "Co-operative"}],
    "player_perspectives": [{"name": "Third person"}],
    "multiplayer_modes": [
        {"platform": 130, "offlinecoopmax": 2, "onlinemax": 0},
        {"platform": 999, "offlinemax": 8, "onlinemax": 4},
    ],
    "language_supports": [
        {"language": {"name": "German"}, "language_support_type": {"name": "Audio"}},
        {"language": {"name": "German"}, "language_support_type": {"name": "Subtitles"}},
        {"language": {"name": "German"}, "language_support_type": {"name": "Subtitles"}},
        {"language": {"name": "Japanese"}, "language_support_type": {"name": "Interface"}},
        {"language": {}},
    ],
}


@pytest.fixture
def igdb(db: None, monkeypatch: pytest.MonkeyPatch) -> None:
    save("igdb", enabled=True, secrets={"client_id": "id", "client_secret": "secret"})
    cache.clear()

    def api(url: str, content: str = "", **kwargs: Any) -> httpx.Response:
        if url.endswith("/game_time_to_beats"):
            return response(json=[{"hastily": 45000, "normally": 72000, "completely": None}])
        return response(json=[GAME])

    monkeypatch.setattr(
        "httpx.post",
        router(
            {
                "https://id.twitch.tv": lambda *a, **k: response(json={"access_token": "t"}),
                "https://api.igdb.com": api,
            }
        ),
    )


def test_igdb_tells_how_it_is_played(igdb: None) -> None:
    record = IGDBSource().get("26758", "130")
    assert record is not None
    assert record.url == "https://www.igdb.com/games/super-mario-odyssey"
    # IGDB's collections are series; its franchises the brand above them.
    assert (record.series, record.franchises) == (["Super Mario 3D"], ["Mario"])
    assert record.game_modes == ["Single player", "Co-operative"]
    assert record.perspectives == ["Third person"]
    # This platform's multiplayer only: two side by side, none online.
    assert (record.players_offline, record.players_online) == (2, None)
    assert record.languages == {"German": ["audio", "subtitles"], "Japanese": ["interface"]}
    assert record.play_times == {"main": 12.5, "extra": 20.0}
    # Search results go without the extra request for play times.
    assert IGDBSource().search("Mario", "130")[0].play_times == {}


def test_import_keeps_it(igdb: None, switch: Platform) -> None:
    record = IGDBSource().get("26758", "130")
    assert record is not None
    release = import_record(record, switch, "pal")
    work = release.work
    assert [s.name for s in work.series.all()] == ["Super Mario 3D"]
    assert [f.name for f in work.franchises.all()] == ["Mario"]
    assert work.game_modes == ["Single player", "Co-operative"]
    assert work.perspectives == ["Third person"]
    assert work.languages["German"] == ["audio", "subtitles"]
    assert (release.players_offline, release.players_online) == (2, None)
    fact = WorkFact.objects.get(work=work, source="igdb")
    assert fact.values == {"main": 12.5, "extra": 20.0}
    assert fact.url == "https://www.igdb.com/games/super-mario-odyssey"


def test_matching_offers_it(
    igdb: None, make_release: Callable[..., Release], switch: Platform, api: Any
) -> None:
    release = make_release("Mario Odyssey", switch)
    changes = {
        c.id.split(".", 1)[-1]: c for c in metadata.preview(release.work, "igdb", "26758").changes
    }
    for name in (
        "series",
        "franchises",
        "game_modes",
        "perspectives",
        "languages",
        "players_offline",
    ):
        assert changes[name].kind == "fill", name
    assert changes["languages"].proposed.text == "German (audio, subtitles), Japanese (interface)"
    chosen = [
        c.id
        for c in changes.values()
        if c.field in ("series", "franchises", "game_modes", "languages", "players_offline")
    ]
    metadata.apply(release.work, "igdb", "26758", chosen)
    release.refresh_from_db()
    work = release.work
    work.refresh_from_db()
    assert [s.name for s in work.series.all()] == ["Super Mario 3D"]
    assert [f.name for f in work.franchises.all()] == ["Mario"]
    assert work.game_modes == ["Single player", "Co-operative"]
    assert work.perspectives == []  # not chosen
    assert release.players_offline == 2
    # Play times come along whenever the game is matched.
    assert WorkFact.objects.get(work=work, source="igdb").values["main"] == 12.5
    # Shown with every release.
    body = api.get(f"/catalog/releases/{release.pk}").json()
    assert body["game_modes"] == ["Single player", "Co-operative"]
    assert body["players_offline"] == 2
    assert body["facts"]["igdb"]["values"]["extra"] == 20.0
    # Nothing left to offer for what was taken.
    left = {c.field for c in metadata.preview(work, "igdb", "26758").changes}
    assert not left & {"series", "franchises", "game_modes", "languages", "players_offline"}
