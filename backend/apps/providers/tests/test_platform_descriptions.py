"""Platforms described by Wikipedia and IGDB: texts, facts, logos, photos and icons."""

from io import BytesIO
from typing import Any

import httpx
import pytest
from django.core.cache import cache
from PIL import Image

from apps.catalog.models import Company, Platform
from apps.providers.services.integrations import save
from apps.providers.sources.igdb import IGDBSource
from apps.providers.sources.wikipedia import WikipediaSource

from .fakes import response, router


def claim(value: Any, rank: str = "normal") -> dict[str, Any]:
    return {"rank": rank, "mainsnak": {"datavalue": {"value": value}}}


def item(qid: str) -> dict[str, str]:
    return {"id": qid}


def year(value: int) -> dict[str, Any]:
    return {"time": f"+{value}-03-03T00:00:00Z", "precision": 11}


SWITCH = {
    "claims": {
        "P31": [claim(item("Q10929058"))],  # "product model": known by its IGDB id
        "P5795": [claim("switch")],
        "P176": [claim(item("Q8093"))],
        "P577": [claim(year(2017))],
        "P2669": [claim(year(2025))],
        "P155": [claim(item("Q56942")), claim(item("Q203597")), claim(item("Q999"))],
        "P156": [claim(item("Q122761124"))],
        "P1813": [claim({"text": "NSW", "language": "en"})],
        "P154": [claim("Nintendo Switch logo.svg")],
        "P8972": [claim("Switch small.svg")],
        "P18": [claim("Switch console.jpg")],
    },
    "sitelinks": {"dewiki": {"title": "Nintendo Switch"}, "enwiki": {"title": "Nintendo Switch"}},
    "labels": {"de": {"value": "Nintendo Switch"}},
}
TOY = {"claims": {"P31": [claim(item("Q1"))]}, "sitelinks": {"dewiki": {"title": "Switch"}}}
LABELS = {
    "Q8093": {"en": {"value": "Nintendo"}},
    "Q56942": {"de": {"value": "Wii U"}},
    "Q203597": {"de": {"value": "Nintendo 3DS"}},
    "Q122761124": {"de": {"value": "Nintendo Switch 2"}},
    "Q999": {},
}
IGDB_SWITCH = {
    "id": 130,
    "name": "Nintendo Switch",
    "abbreviation": "Switch",
    "generation": 8,
    "platform_logo": {"image_id": "plgu"},
    "versions": [
        {"name": "Lite", "summary": "Smaller."},
        {
            "name": "Initial version",
            "summary": "A hybrid.",
            "platform_version_release_dates": [{"date": 1488499200}, {"date": None}],
            "companies": [
                {"company": {"id": 70, "name": "Nintendo"}, "manufacturer": True},
            ],
        },
    ],
}


def png() -> bytes:
    out = BytesIO()
    Image.new("RGB", (2, 2)).save(out, "PNG")
    return out.getvalue()


@pytest.fixture
def sources(db: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Wikidata knows the Switch (Q19610114) and a toy; IGDB the Switch (130) and an
    unrelated one; both image hosts answer with a PNG."""
    save("wikipedia", enabled=True)
    save("igdb", enabled=True, secrets={"client_id": "id", "client_secret": "secret"})
    cache.clear()
    items = {"Q19610114": SWITCH, "Q5": TOY}

    def wikidata(url: str, params: dict[str, str], **kwargs: Any) -> httpx.Response:
        if params["action"] == "wbsearchentities":
            found = [{"id": q, "label": "Nintendo Switch"} for q in items]
            return response(json={"search": found})
        ids = params["ids"].split("|")
        if params["props"] == "labels":
            return response(json={"entities": {q: {"labels": LABELS[q]} for q in ids}})
        return response(json={"entities": {q: items[q] for q in ids if q in items}})

    def wiki(text: str) -> Any:
        def answer(url: str, params: dict[str, str], **kwargs: Any) -> httpx.Response:
            pages = [{"title": t, "extract": text} for t in params["titles"].split("|")]
            return response(json={"query": {"pages": pages}})

        return answer

    def images(url: str, *args: Any, **kwargs: Any) -> httpx.Response:
        return response(content=png(), ctype="image/png")

    monkeypatch.setattr(
        "httpx.get",
        router(
            {
                "https://www.wikidata.org": wikidata,
                "https://de.wikipedia.org": wiki("Eine Konsole."),
                "https://en.wikipedia.org": wiki("A console."),
                "https://upload.wikimedia.org": images,
                "https://images.igdb.com": images,
            }
        ),
    )

    def platforms(url: str, content: str = "", **kwargs: Any) -> httpx.Response:
        assert url.endswith("/platforms")
        if "where id = 130;" in content:
            return response(json=[IGDB_SWITCH])
        if "Switch" in content:
            return response(json=[{"id": 4, "name": "Switch Box"}, IGDB_SWITCH])
        return response(json=[])

    monkeypatch.setattr(
        "httpx.post",
        router(
            {
                "https://id.twitch.tv": lambda *a, **k: response(json={"access_token": "t"}),
                "https://api.igdb.com": platforms,
            }
        ),
    )


def test_wikipedia_describes_platforms(sources: None) -> None:
    source = WikipediaSource()
    found = source.describe("Nintendo Switch", "platforms", "de")
    assert [(r.external_id, r.confident) for r in found] == [("Q19610114", True), ("Q5", False)]
    record = source.description("Q19610114", "de", "platforms")
    assert record is not None
    assert record.platform is not None
    facts = record.platform
    assert (facts.short_name, facts.released, facts.discontinued) == ("NSW", 2017, 2025)
    assert facts.manufacturer is not None
    assert facts.manufacturer.names == ("Nintendo",)
    assert [r.names[0] for r in facts.predecessors] == ["Wii U", "Nintendo 3DS"]
    assert [r.external_id for r in facts.successors] == ["Q122761124"]
    assert [(i.label, i.kind) for i in record.images] == [
        ("Nintendo Switch logo", "logo"),
        ("Switch small", "icon"),
        ("Switch console", "photo"),
    ]
    # Companies get no photos and no platform facts.
    company = source.description("Q19610114", "de", "companies")
    assert company is not None
    assert company.platform is None
    assert [i.kind for i in company.images] == ["logo", "icon"]


def test_igdb_describes_platforms(sources: None) -> None:
    source = IGDBSource()
    found = source.describe("Switch", "platforms")
    assert [(r.external_id, r.confident) for r in found] == [("130", True), ("4", False)]
    assert found[0].text == "A hybrid.\n\nSource: IGDB"
    assert found[0].platform is None
    assert source.describe("Nothing", "platforms") == []
    record = source.description("130", "de", "platforms")
    assert record is not None
    assert record.platform is not None
    assert record.platform.generation == 8
    assert record.platform.released == 2017
    assert record.platform.short_name == "Switch"
    assert record.platform.manufacturer is not None
    assert record.platform.manufacturer.names == ("Nintendo",)
    assert [i.url.rsplit("/", 1)[1] for i in record.images] == ["plgu.png"]
    assert source.description("131", "de", "platforms") is None


def test_platform_takes_a_description(api: Any, sources: None, switch: Platform) -> None:
    nintendo = Company.objects.create(name="NINTENDO")
    wii_u = Platform.objects.get(slug="wii-u")
    three_ds = Platform.objects.get(slug="3ds")
    three_ds.external_ids = {**three_ds.external_ids, "wikipedia": "Q203597"}
    three_ds.name = "3DS (old)"
    three_ds.save()
    Platform.objects.filter(pk=switch.pk).update(
        short_name="", manufacturer="", release_year=None, external_ids={}
    )
    url = f"/catalog/platforms/{switch.pk}/description/wikipedia"
    found = api.get(f"{url}/candidates").json()
    assert found[0]["external_id"] == "Q19610114"
    assert found[0]["has_image"] is True
    assert api.post(url, {"external_id": "Q19610114", "image": True}).json()["image"] is True
    switch.refresh_from_db()
    assert switch.descriptions["de"].startswith("Eine Konsole.")
    assert (switch.short_name, switch.manufacturer, switch.release_year) == (
        "NSW",
        nintendo.name,
        2017,
    )
    assert switch.discontinued == 2025
    assert switch.image
    assert set(switch.predecessors.all()) == {wii_u, three_ds}
    assert list(switch.successors.all()) == [Platform.objects.get(slug="switch-2")]

    # IGDB: its id stays a number; what we have stays, generation is new.
    url = f"/catalog/platforms/{switch.pk}/description/igdb"
    assert api.post(url, {"external_id": "130"}).status_code == 200
    switch.refresh_from_db()
    assert switch.external_ids == {"wikipedia": "Q19610114", "igdb": 130}
    assert (switch.short_name, switch.generation) == ("NSW", 8)
    assert switch.descriptions["en"] == "A hybrid.\n\nSource: IGDB"

    detail = api.get(f"/catalog/platforms/{switch.pk}").json()
    assert detail["manufacturer_company"] == {"id": str(nintendo.pk), "name": "NINTENDO"}
    assert [p["name"] for p in detail["predecessors"]] == ["3DS (old)", "Nintendo Wii U"]
    assert [p["name"] for p in detail["successors"]] == ["Nintendo Switch 2"]
    assert detail["description"].startswith("Eine Konsole.")
    assert detail["can_describe"] is True


def test_platform_pictures_and_icons(api: Any, sources: None, switch: Platform) -> None:
    switch.external_ids = {"wikipedia": "Q19610114", "igdb": 130}
    switch.save()
    url = f"/catalog/platforms/{switch.pk}/images"
    found = api.get(url).json()
    assert [(c["source"], c["kind"]) for c in found] == [
        ("igdb", "logo"),
        ("wikipedia", "logo"),
        ("wikipedia", "icon"),
        ("wikipedia", "photo"),
    ]
    taken = api.post(url, {"token": found[2]["token"], "target": "icon"}).json()
    assert taken["icon_url"]
    assert taken["image_url"] is None
    taken = api.post(url, {"token": found[3]["token"]}).json()
    assert taken["image_url"]
    switch.refresh_from_db()
    assert switch.icon_image
    assert switch.image

    # Only platforms have a badge icon.
    company = Company.objects.create(name="Nintendo", external_ids={"wikipedia": "Q19610114"})
    token = api.get(f"/catalog/companies/{company.pk}/images").json()[0]["token"]
    answer = api.post(f"/catalog/companies/{company.pk}/images", {"token": token, "target": "icon"})
    assert answer.status_code == 400


def test_commons_search_and_photos(
    api: Any, sources: None, switch: Platform, monkeypatch: pytest.MonkeyPatch
) -> None:
    big = BytesIO()
    Image.effect_noise((2400, 1800), 90).convert("RGB").save(big, "BMP")  # incompressible
    photo = BytesIO()
    Image.open(BytesIO(big.getvalue())).save(photo, "PNG")
    assert len(photo.getvalue()) > 2 * 1024 * 1024
    inner = httpx.get

    def get(url: str, *args: Any, **kwargs: Any) -> httpx.Response:
        if url.startswith("https://commons.wikimedia.org"):
            params = kwargs["params"]
            assert params["gsrsearch"] == "Switch console"
            assert params["iiurlwidth"] == "1600"
            commons = "https://upload.wikimedia.org/wikipedia/commons/"
            pages = {
                "2": {"index": 2, "title": "File:Logo.svg", "imageinfo": [
                    {"mime": "image/svg+xml", "url": f"{commons}a/ab/Logo.svg"}]},
                "1": {"index": 1, "title": "File:Switch.jpg", "imageinfo": [
                    {"mime": "image/jpeg", "url": f"{commons}c/cd/Switch.jpg",
                     "thumburl": f"{commons}thumb/c/cd/Switch.jpg/1600px-Switch.jpg"}]},
                "3": {"index": 3, "title": "File:Clip.webm", "imageinfo": [
                    {"mime": "video/webm", "url": f"{commons}e/ef/Clip.webm"}]},
                "4": {"index": 4, "title": "File:Elsewhere.png", "imageinfo": [
                    {"mime": "image/png", "thumburl": "https://example.com/x.png"}]},
            }  # fmt: skip
            return response(json={"query": {"pages": pages}})
        if "1600px-Switch" in url:
            return response(content=photo.getvalue(), ctype="image/png")
        return inner(url, *args, **kwargs)

    monkeypatch.setattr("httpx.get", get)
    found = api.get("/catalog/commons-images", {"q": " Switch console "}).json()
    assert [(c["label"], c["kind"]) for c in found] == [("Switch", "photo"), ("Logo", "logo")]
    assert api.get("/catalog/commons-images", {"q": " "}).json() == []

    # Too big to keep as it is: shrunk.
    taken = api.post(
        f"/catalog/platforms/{switch.pk}/images", {"token": found[0]["token"], "target": "photo"}
    ).json()
    assert taken["photo_url"]
    assert taken["image_url"] is None
    switch.refresh_from_db()
    with Image.open(switch.photo) as kept:
        assert max(kept.size) == 1600
    assert switch.photo.size <= 2 * 1024 * 1024
    detail = api.get(f"/catalog/platforms/{switch.pk}").json()
    assert detail["photo_url"] == taken["photo_url"]

    # Companies have no photo slot.
    company = Company.objects.create(name="Nintendo")
    answer = api.post(
        f"/catalog/companies/{company.pk}/images", {"token": found[1]["token"], "target": "photo"}
    )
    assert answer.status_code == 400


def test_commons_search_needs_wikipedia(api: Any, db: None) -> None:
    assert api.get("/catalog/commons-images", {"q": "x"}).status_code == 400


def test_fit_picture_leaves_what_fits() -> None:
    from apps.core.services.images import fit_picture

    svg = b"<svg/>" + b" " * (3 * 1024 * 1024)
    assert fit_picture(svg) == svg
    junk = b"x" * (3 * 1024 * 1024)
    assert fit_picture(junk) == junk
    assert fit_picture(png()) == png()
    rgba = BytesIO()
    Image.effect_noise((900, 900), 90).convert("RGBA").save(rgba, "PNG")
    small = fit_picture(rgba.getvalue(), max_bytes=1000, max_side=100)
    with Image.open(BytesIO(small)) as image:
        assert image.format == "PNG"
        assert image.size == (100, 100)


def test_redirects_have_no_text(db: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """de "Game Boy Color" only redirects to "Game Boy": no text of its own."""

    def wiki(url: str, params: dict[str, str], **kwargs: Any) -> httpx.Response:
        assert params["redirects"] == "1"
        return response(
            json={
                "query": {
                    "redirects": [{"from": "Game Boy Color", "to": "Game Boy"}],
                    "pages": [
                        {"title": "Game Boy", "extract": "Der Game Boy …"},
                        {"title": "Wii", "extract": "Die Wii …"},
                    ],
                }
            }
        )

    monkeypatch.setattr("httpx.get", router({"https://de.wikipedia.org": wiki}))
    extracts = WikipediaSource()._extracts(["Game Boy Color", "Wii"], "de")
    assert extracts.get("Game Boy Color") is None
    assert extracts["Wii"] == "Die Wii …"


def test_igdb_text_only_of_the_original_model(sources: None) -> None:
    pc = {"id": 6, "name": "PC", "versions": [{"name": "Windows 2.0", "summary": "Old."}]}
    assert IGDBSource()._platform_record(pc, "pc").text == ""
