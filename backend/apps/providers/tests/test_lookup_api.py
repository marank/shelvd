from collections.abc import Callable
from typing import Any

import httpx
import pytest
from django.core.cache import cache

from apps.catalog.models import Barcode, Platform, Release, Work
from apps.providers.services.integrations import save
from apps.providers.sources import ProviderError
from apps.providers.sources.igdb import IGDBSource

from .fakes import IGDB_GAME, response, router

PNG = b"\x89PNG fake"


@pytest.fixture
def online(db: None, monkeypatch: pytest.MonkeyPatch) -> None:
    save("igdb", enabled=True, secrets={"client_id": "id", "client_secret": "secret"})
    cache.clear()

    def games(url: str, content: str = "", **kwargs: Any) -> httpx.Response:
        return response(json=[] if "where id = 1;" in content else [IGDB_GAME])

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


def test_providers_listed(api: Any) -> None:
    listed = api.get("/lookup/providers").json()
    # Built-in ones first; add-ons (backend/addons) may add more after them.
    assert [(p["name"], p["kind"], p["enabled"]) for p in listed][:6] == [
        ("igdb", "metadata", False),
        ("wikipedia", "metadata", False),
        ("hltb", "facts", False),
        ("opencritic", "facts", False),
        ("thegamesdb", "covers", False),
        ("screenscraper", "covers", False),
    ]
    # Switched on but without its required key, a source still counts as off.
    save("igdb", enabled=True)
    assert api.get("/lookup/providers").json()[0]["enabled"] is False


def test_barcode_scan_to_import(api: Any, online: None, switch: Platform) -> None:
    assert api.get("/lookup/barcode/123").status_code == 400
    result = api.get("/lookup/barcode/0045496590420").json()
    assert result == {"code": "0045496590420", "known": []}
    search = api.get("/lookup/search", {"q": "Super Mario Odyssey"}).json()
    # Unknown IGDB platforms (999) are dropped.
    assert [c["platform_name"] for c in search["candidates"]] == ["Nintendo Switch"]
    candidate = search["candidates"][0]
    assert candidate["year"] == 2017

    imported = api.post(
        "/lookup/import",
        {
            "provider": "igdb",
            "external_id": candidate["external_id"],
            "platform_id": str(switch.pk),
            "region": "na",
            "barcode": "0045496590420",
        },
    )
    assert imported.status_code == 201, imported.json()
    release = imported.json()
    assert release["title"] == "Super Mario Odyssey"
    assert release["publisher"]["name"] == "Nintendo"
    assert [g["name"] for g in release["genres"]] == ["Adventure", "Jump 'n' Run"]
    assert release["cover_url"].endswith(".png")
    # IGDB's cover is the game's; without box art the release shows that one.
    assert release["cover_source"] == ""
    assert Work.objects.get(pk=release["work_id"]).cover
    assert release["barcodes"] == ["0045496590420"]
    # Each region gets its own date from IGDB.
    assert release["release_date"] == "2017-10-27"
    assert release["release_precision"] == "day"

    # The next scan of the same code is answered locally.
    again = api.get("/lookup/barcode/045496590420").json()
    assert [r["id"] for r in again["known"]] == [release["id"]]

    # Importing the PAL release reuses the work.
    pal = api.post(
        "/lookup/import",
        {
            "provider": "igdb",
            "external_id": "26758",
            "platform_id": str(switch.pk),
            "region": "pal",
        },
    ).json()
    assert pal["work_id"] == release["work_id"]
    assert pal["release_date"] == "2017-10-27"
    assert Work.objects.count() == 1


def test_import_errors(
    api: Any, online: None, switch: Platform, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = {"external_id": "26758", "platform_id": str(switch.pk), "region": "pal"}
    assert api.post("/lookup/import", {**base, "provider": "moby"}).status_code == 400
    missing = {**base, "provider": "igdb", "external_id": "1"}
    assert api.post("/lookup/import", missing).status_code == 404

    def broken(*args: Any, **kwargs: Any) -> None:
        raise ProviderError("down")

    monkeypatch.setattr(IGDBSource, "get", broken)
    assert api.post("/lookup/import", {**base, "provider": "igdb"}).status_code == 502


def test_search(api: Any, online: None, switch: Platform, monkeypatch: pytest.MonkeyPatch) -> None:
    assert api.get("/lookup/search", {"q": " "}).status_code == 400
    found = api.get("/lookup/search", {"q": "odyssey", "platform": str(switch.pk)}).json()
    assert len(found["candidates"]) == 1

    def broken(*args: Any, **kwargs: Any) -> None:
        raise ProviderError("down")

    monkeypatch.setattr(IGDBSource, "search", broken)
    assert api.get("/lookup/search", {"q": "odyssey"}).json()["errors"] == ["igdb"]


def test_cover_download_rejects(
    online: None,
    monkeypatch: pytest.MonkeyPatch,
    make_release: Callable[..., Release],
    switch: Platform,
) -> None:
    from apps.providers.services.importer import download_cover

    release = make_release("X", switch)
    monkeypatch.setattr("httpx.get", lambda *a, **k: response(content=b"<html>", ctype="text/html"))
    assert download_cover(release, "https://images.igdb.com/x", "igdb") is False
    monkeypatch.setattr("httpx.get", router({}))
    assert download_cover(release, "https://images.igdb.com/x", "igdb") is False
    assert not Barcode.objects.exists()


def test_article_codes(
    api: Any, online: None, nds: Platform, make_release: Callable[..., Release]
) -> None:
    """Some boxes only carry an article number (Code 128): it's matched against product
    codes and remembered like a barcode once confirmed."""
    heartgold = make_release("Pokémon HeartGold", nds)
    heartgold.product_code = "NTR-IPKD-NOE"
    heartgold.save()
    by_product = api.get("/lookup/barcode/ntr-ipkd-noe").json()
    assert by_product["code"] == "NTR-IPKD-NOE"
    assert [r["id"] for r in by_product["known"]] == [str(heartgold.pk)]

    unknown = api.get("/lookup/barcode/1836540t").json()
    assert unknown["known"] == []

    attached = api.post(f"/catalog/releases/{heartgold.pk}/barcodes", {"code": "1836540T"})
    assert attached.json()["barcodes"] == ["1836540T"]
    again = api.get("/lookup/barcode/1836540T").json()
    assert [r["id"] for r in again["known"]] == [str(heartgold.pk)]
    # A code with GTIN digits but a wrong check digit is a misread, not an article number.
    assert api.get("/lookup/barcode/4006381333932").status_code == 400


def test_all_digit_article_number(
    api: Any, online: None, nds: Platform, make_release: Callable[..., Release]
) -> None:
    """Digits of no GTIN length are an article number: matched against product codes."""
    game = make_release("Pokémon HeartGold", nds)
    game.product_code = "1234567"
    game.save()
    found = api.get("/lookup/barcode/1234567").json()
    assert [r["id"] for r in found["known"]] == [str(game.pk)]
