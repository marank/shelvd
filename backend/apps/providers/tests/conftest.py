from typing import Any

import httpx
import pytest
from django.core.cache import cache

from apps.providers.services.integrations import save

from .fakes import IGDB_GAME, response, router

PNG = b"\x89PNG fake"


@pytest.fixture
def igdb(db: None, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """IGDB knows Super Mario Odyssey (id 26758) and nothing else; returns the queries."""
    save("igdb", enabled=True, secrets={"client_id": "id", "client_secret": "secret"})
    cache.clear()
    queries: list[str] = []

    def games(url: str, content: str = "", **kwargs: Any) -> httpx.Response:
        queries.append(content)
        if "where id = " in content and "where id = 26758;" not in content:
            return response(json=[])
        return response(json=[IGDB_GAME])

    monkeypatch.setattr(
        "httpx.post",
        router(
            {
                "https://id.twitch.tv": lambda *a, **k: response(json={"access_token": "t"}),
                "https://api.igdb.com": games,
            }
        ),
    )
    monkeypatch.setattr(
        "httpx.get",
        router(
            {
                "https://images.igdb.com": lambda *a, **k: response(content=PNG, ctype="image/png"),
            }
        ),
    )
    return queries
