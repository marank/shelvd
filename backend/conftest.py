"""Shared fixtures. The platform seed migration runs in the test database too."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.catalog.models import Company, Genre, Platform, Release, Work
from apps.collection.models import Item, Library


@pytest.fixture(autouse=True)
def _fast_hashing(settings: Any, tmp_path: Any) -> None:
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.IGDB_CLIENT_ID = ""
    settings.IGDB_CLIENT_SECRET = ""
    settings.UPCITEMDB_ENABLED = False


@pytest.fixture
def user(db: None) -> User:
    """The admin: keeps the catalog (most tests change it). `other` is a plain user."""
    return User.objects.create_user("alice", "alice@example.com", "pw-alice-123", is_staff=True)


@pytest.fixture
def other(db: None) -> User:
    return User.objects.create_user("bob", "bob@example.com", "pw-bob-123")


class Api:
    """Test client speaking JSON to /api."""

    def __init__(self, client: Client) -> None:
        self.client = client

    def _send(self, method: str, path: str, data: Any = None) -> Any:
        call: Callable[..., Any] = getattr(self.client, method)
        if data is None:
            return call(f"/api{path}")
        return call(f"/api{path}", data=json.dumps(data), content_type="application/json")

    def get(self, path: str, params: Any = None) -> Any:
        return self.client.get(f"/api{path}", params or {})

    def post(self, path: str, data: Any = None) -> Any:
        return self._send("post", path, data if data is not None else {})

    def patch(self, path: str, data: Any) -> Any:
        return self._send("patch", path, data)

    def put(self, path: str, data: Any) -> Any:
        return self._send("put", path, data)

    def delete(self, path: str) -> Any:
        return self._send("delete", path)


@pytest.fixture
def api(user: User) -> Api:
    client = Client()
    client.force_login(user)
    return Api(client)


@pytest.fixture
def other_api(other: User) -> Api:
    client = Client()
    client.force_login(other)
    return Api(client)


@pytest.fixture
def anon_api(db: None) -> Api:
    return Api(Client())


@pytest.fixture
def switch(db: None) -> Platform:
    return Platform.objects.get(slug="switch")


@pytest.fixture
def nds(db: None) -> Platform:
    return Platform.objects.get(slug="nds")


@pytest.fixture
def make_release(db: None) -> Callable[..., Release]:
    def make(
        title: str,
        platform: Platform,
        *,
        year: int | None = None,
        publisher: str = "",
        genres: tuple[str, ...] = (),
        developers: tuple[str, ...] = (),
        region: str = "pal",
    ) -> Release:
        import datetime

        work = Work.objects.create(
            title=title, first_release_date=datetime.date(year, 1, 1) if year else None
        )
        work.genres.set([Genre.objects.get_or_create(name=g)[0] for g in genres])
        work.developers.set([Company.objects.get_or_create(name=d)[0] for d in developers])
        return Release.objects.create(
            work=work,
            platform=platform,
            region=region,
            publisher=Company.objects.get_or_create(name=publisher)[0] if publisher else None,
        )

    return make


@pytest.fixture
def library(user: User) -> Library:
    return Library.objects.create(name="Games", owner=user)


@pytest.fixture
def stocked(
    library: Library, make_release: Callable[..., Release], switch: Platform, nds: Platform
) -> dict[str, Item]:
    """Three items: two Nintendo-published games and one from another publisher."""
    mk8 = make_release(
        "Mario Kart 8 Deluxe", switch, year=2017, publisher="Nintendo", genres=("Racing",)
    )
    zelda = make_release(
        "Zelda: Breath of the Wild",
        switch,
        year=2017,
        publisher="Nintendo",
        genres=("Adventure", "RPG"),
        developers=("Nintendo EPD",),
    )
    sonic = make_release("Sonic Rush", nds, year=2005, publisher="Sega", genres=("Platformer",))
    return {
        "mk8": Item.objects.create(library=library, release=mk8),
        "zelda": Item.objects.create(library=library, release=zelda, notes="signed copy"),
        "sonic": Item.objects.create(library=library, release=sonic, format="physical"),
    }
