from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.catalog.models import Platform, Release


def png() -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", (2, 2), (255, 0, 0, 255)).save(buffer, "PNG")
    return buffer.getvalue()


def gif() -> bytes:
    buffer = BytesIO()
    Image.new("P", (2, 2)).save(buffer, "GIF")
    return buffer.getvalue()


SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"><defs><path id="p" d="M0 0h8v8z"/></defs><use href="#p" fill="red"/></svg>'  # noqa: E501


def upload(api: Any, platform_id: str, content: bytes, name: str = "icon.svg") -> Any:
    return api.client.post(
        f"/api/catalog/platforms/{platform_id}/icon",
        {"file": SimpleUploadedFile(name, content)},
    )


def test_create_change_and_delete(api: Any) -> None:
    created = api.post(
        "/catalog/platforms",
        {"name": " Analogue Pocket ", "short_name": "Pocket", "manufacturer": "Analogue",
         "release_year": 2021, "color": "#112233", "icon": "handheld", "igdb_id": 999},
    )  # fmt: skip
    assert created.status_code == 201, created.json()
    platform = created.json()
    assert platform["name"] == "Analogue Pocket"
    assert platform["slug"] == "analogue-pocket"
    assert (platform["color"], platform["icon"], platform["icon_url"]) == (
        "#112233",
        "handheld",
        None,
    )
    assert (platform["igdb_id"], platform["release_count"]) == (999, 0)
    assert api.post("/catalog/platforms", {"name": "Analogue Pocket"}).status_code == 409
    # Same slug base, different name: the slug gets a suffix.
    assert api.post("/catalog/platforms", {"name": "Analogue-Pocket"}).json()["slug"] == (
        "analogue-pocket-2"
    )

    path = f"/catalog/platforms/{platform['id']}"
    patched = api.patch(path, {"color": "", "icon": "", "igdb_id": None, "name": None}).json()
    assert (patched["color"], patched["icon"], patched["igdb_id"]) == ("", "", None)
    assert patched["name"] == "Analogue Pocket"
    assert Platform.objects.get(pk=platform["id"]).external_ids == {}
    assert api.patch(path, {"color": "red"}).status_code == 400
    assert api.patch(path, {"icon": "nintendo-logo"}).status_code == 400
    assert api.patch(path, {"name": "  "}).status_code == 400
    assert api.patch(path, {"name": "Nintendo Switch"}).status_code == 409
    assert api.get(path).json()["name"] == "Analogue Pocket"

    assert api.delete(path).status_code == 204
    assert api.get(path).status_code == 404


def test_platform_in_use_stays(
    api: Any, make_release: Callable[..., Release], switch: Platform
) -> None:
    make_release("Mario", switch)
    assert api.get(f"/catalog/platforms/{switch.pk}").json()["release_count"] == 1
    assert api.delete(f"/catalog/platforms/{switch.pk}").status_code == 409
    listed = api.get("/catalog/platforms").json()
    entry = next(p for p in listed if p["slug"] == "switch")
    assert {"color", "icon", "icon_url"} <= entry.keys()


def test_icon_upload(api: Any, switch: Platform) -> None:
    result = upload(api, str(switch.pk), SVG)
    assert result.status_code == 200, result.json()
    url = result.json()["icon_url"]
    assert url.startswith("/media/platforms/")
    assert url.endswith(".svg")
    # A raster icon replaces it (and the old file).
    old = Platform.objects.get(pk=switch.pk).icon_image.path
    raster = upload(api, str(switch.pk), png(), "icon.png").json()["icon_url"]
    assert raster.endswith(".png")
    assert not Path(old).exists()
    removed = api.delete(f"/catalog/platforms/{switch.pk}/icon").json()
    assert removed["icon_url"] is None
    assert api.delete(f"/catalog/platforms/{switch.pk}/icon").status_code == 200


@pytest.mark.parametrize(
    "content",
    [
        b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>',
        b'<svg xmlns="http://www.w3.org/2000/svg"><a href="javascript:alert(1)"><path/></a></svg>',
        b'<svg xmlns="http://www.w3.org/2000/svg" xmlns:x="http://www.w3.org/1999/xlink">'
        b'<image x:href="https://evil.example/x.png"/></svg>',
        b'<svg xmlns="http://www.w3.org/2000/svg"><path style="fill:url(https://e.x/a)"/></svg>',
        b'<svg xmlns="http://www.w3.org/2000/svg"><foreignObject><div/></foreignObject></svg>',
    ],
)
def test_unsafe_svgs_rejected(api: Any, switch: Platform, content: bytes) -> None:
    result = upload(api, str(switch.pk), content)
    assert result.status_code == 400
    assert "Skripte oder Links" in result.json()["detail"]
    assert not Platform.objects.get(pk=switch.pk).icon_image


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"<html><body/></html>", "kein Bild"),
        (b"<svg><unclosed", "kein Bild"),
        (gif(), "Nur SVG-, JPEG-"),
        (b"\x89PNG\r\n\x1a\n broken", "kein Bild"),
        (b"x" * (257 * 1024), "zu groß"),
    ],
)
def test_bad_icons_rejected(api: Any, switch: Platform, content: bytes, message: str) -> None:
    result = upload(api, str(switch.pk), content, "icon.bin")
    assert result.status_code == 400
    assert message in result.json()["detail"]


def test_platform_page_fields(api: Any, other_api: Any, switch: Platform) -> None:
    wii_u = Platform.objects.get(slug="wii-u")
    path = f"/catalog/platforms/{switch.pk}"
    patched = api.patch(
        path,
        {
            "descriptions": {"de": " Eine Konsole. ", "en": ""},
            "generation": 8,
            "discontinued": 2025,
            "predecessors": [str(wii_u.pk), str(switch.pk)],
        },
    )
    assert patched.status_code == 200, patched.json()
    page = patched.json()
    assert page["descriptions"] == {"de": "Eine Konsole."}
    assert (page["description"], page["description_language"]) == ("Eine Konsole.", "de")
    assert (page["generation"], page["discontinued"]) == (8, 2025)
    assert [p["id"] for p in page["predecessors"]] == [str(wii_u.pk)]  # never itself
    wii = api.get(f"/catalog/platforms/{wii_u.pk}").json()
    assert [p["name"] for p in wii["successors"]] == [switch.name]
    assert page["manufacturer_company"] is None  # no company "Nintendo" in the catalog

    for bad in ({"generation": 0}, {"discontinued": 99}, {"descriptions": {"xx": "?"}}):
        assert api.patch(path, bad).status_code == 400, bad
    unknown = "00000000-0000-0000-0000-000000000000"
    assert api.patch(path, {"predecessors": [unknown]}).status_code == 400
    assert api.patch(path, {"predecessors": []}).json()["predecessors"] == []
    assert other_api.patch(path, {"generation": 9}).status_code == 403


def test_platform_picture(api: Any, switch: Platform) -> None:
    path = f"/api/catalog/platforms/{switch.pk}/image"
    answer = api.client.post(path, {"file": SimpleUploadedFile("photo.png", png())})
    assert answer.status_code == 200
    assert answer.json()["image_url"].endswith(".png")
    switch.refresh_from_db()
    stored = Path(switch.image.path)
    assert stored.exists()
    assert api.client.delete(path).json()["image_url"] is None
    assert not stored.exists()


def test_platform_games(api: Any, switch: Platform, make_release: Callable[..., Release]) -> None:
    make_release("Zelda", switch)
    make_release("Mario", switch)
    make_release("Halo", Platform.objects.get(slug="xbox"))
    games = api.get(f"/catalog/platforms/{switch.pk}/games").json()
    assert sorted(w["title"] for w in games["works"]) == ["Mario", "Zelda"]
    assert games["related"] == []


def test_platform_photo_and_list(
    api: Any, switch: Platform, make_release: Callable[..., Release]
) -> None:
    make_release("Zelda", switch)
    make_release("Mario", switch)
    path = f"/api/catalog/platforms/{switch.pk}/photo"
    answer = api.client.post(path, {"file": SimpleUploadedFile("photo.png", png())})
    assert answer.status_code == 200
    assert answer.json()["photo_url"].endswith(".png")
    listed = {p["id"]: p for p in api.get("/catalog/platforms").json()}[str(switch.pk)]
    assert listed["photo_url"]
    assert listed["image_url"] is None
    assert listed["game_count"] == 2
    assert api.client.delete(path).json()["photo_url"] is None


def test_dark_icons_are_noted(api: Any, switch: Platform) -> None:
    """A black glyph is inverted on dark backgrounds; colour pictures stay as they are."""
    glyph = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0h8v8z"/></svg>'
    assert upload(api, str(switch.pk), glyph).json()["icon_dark"] is True
    colourful = BytesIO()
    image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    image.paste((230, 0, 18, 255), (0, 0, 6, 6))
    image.save(colourful, "PNG")
    assert upload(api, str(switch.pk), colourful.getvalue(), "i.png").json()["icon_dark"] is False
    assert upload(api, str(switch.pk), glyph).json()["icon_dark"] is True
    removed = api.client.delete(f"/api/catalog/platforms/{switch.pk}/icon").json()
    assert removed["icon_dark"] is False


def test_what_counts_as_a_dark_mark() -> None:
    from apps.core.services.images import is_dark_mark

    def svg(body: str) -> bytes:
        return f'<svg xmlns="http://www.w3.org/2000/svg">{body}</svg>'.encode()

    def raster(fill: tuple[int, int, int, int], transparent: bool = True) -> bytes:
        out = BytesIO()
        image = Image.new("RGBA", (8, 8), (0, 0, 0, 0) if transparent else (255, 255, 255, 255))
        image.paste(fill, (0, 0, 6, 6))
        image.save(out, "PNG")
        return out.getvalue()

    assert is_dark_mark(svg('<path d="M0 0"/>'))  # unfilled: black
    assert is_dark_mark(svg('<path fill="#111" d="M0 0"/><g style="fill:rgb(20, 20, 20)"/>'))
    assert not is_dark_mark(svg('<path fill="#e60012" d="M0 0"/>'))  # colour
    assert not is_dark_mark(svg('<path fill="white" d="M0 0"/><path fill="#fff"/>'))
    assert not is_dark_mark(svg("<g/>"))  # nothing drawn
    assert not is_dark_mark(b"<svg")  # broken
    assert is_dark_mark(raster((10, 10, 10, 255)))
    assert not is_dark_mark(raster((10, 10, 10, 255), transparent=False))  # a block
    assert not is_dark_mark(raster((0, 0, 0, 0)))  # empty
    assert not is_dark_mark(raster((200, 200, 200, 255)))
    assert not is_dark_mark(b"no picture")


def test_a_photo_makes_an_icon() -> None:
    from apps.core.services.images import make_icon

    photo = BytesIO()
    image = Image.new("RGB", (400, 200), (255, 255, 255))
    image.paste((20, 20, 20), (150, 50, 250, 150))  # the device, on white
    image.save(photo, "JPEG")
    with Image.open(BytesIO(make_icon(photo.getvalue()))) as icon:
        # Cut to the device (never scaled up), square, the white gone around it.
        assert icon.format == "PNG"
        assert icon.width == icon.height <= 110
        assert icon.getchannel("A").getpixel((icon.width // 2, icon.height // 2)) == 255
    wide = BytesIO()
    image = Image.new("RGB", (1200, 600), (250, 250, 250))
    image.paste((20, 20, 20), (100, 200, 1100, 400))
    image.save(wide, "PNG")
    with Image.open(BytesIO(make_icon(wide.getvalue()))) as icon:
        assert icon.size == (256, 256)
        assert icon.getchannel("A").getpixel((0, 0)) == 0  # padded, transparent
        assert icon.getchannel("A").getpixel((128, 128)) == 255
    # A busy background stays; SVGs and non-pictures are left alone.
    busy = BytesIO()
    noise = Image.effect_noise((64, 64), 90).convert("RGB")
    noise.save(busy, "PNG")
    with Image.open(BytesIO(make_icon(busy.getvalue()))) as icon:
        assert icon.getchannel("A").getpixel((0, 0)) == 255
    assert make_icon(b"<svg/>") == b"<svg/>"
    assert make_icon(b"junk") == b"junk"
