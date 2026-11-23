import io
from collections.abc import Callable
from typing import Any

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.catalog.models import Barcode, Platform, Release, Work


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 6), "red").save(buffer, "PNG")
    return buffer.getvalue()


def test_platforms_seeded(api: Any) -> None:
    names = {p["slug"] for p in api.get("/catalog/platforms").json()}
    assert {"nds", "3ds", "switch", "switch-2", "ps5"} <= names


def test_requires_login(anon_api: Any) -> None:
    assert anon_api.get("/catalog/platforms").status_code == 401


def test_create_search_update_release(api: Any, switch: Platform, nds: Platform) -> None:
    payload = {
        "title": "Pikmin 4",
        "platform_id": str(switch.pk),
        "publisher": {"name": "Nintendo"},
        "developers": [{"name": "Nintendo EPD"}],
        "genres": [{"name": "Strategy"}],
        "series": [{"name": "Pikmin"}],
        "barcode": "045496598976",
    }
    created = api.post("/catalog/releases", payload)
    assert created.status_code == 201, created.json()
    body = created.json()
    assert body["title"] == "Pikmin 4"
    assert body["barcodes"] == ["0045496598976"]
    assert body["publisher"]["name"] == "Nintendo"
    assert [s["name"] for s in body["series"]] == ["Pikmin"]

    assert [r["id"] for r in api.get("/catalog/releases", {"q": "pikm"}).json()] == [body["id"]]
    by_code = api.get("/catalog/releases", {"q": "0045496598976"}).json()
    assert [r["id"] for r in by_code] == [body["id"]]
    assert api.get("/catalog/releases", {"q": "pikmin", "platform": str(nds.pk)}).json() == []

    second = api.post(
        "/catalog/releases",
        {"title": "Pikmin 4", "platform_id": str(nds.pk), "work_id": body["work_id"]},
    )
    assert second.json()["work_id"] == body["work_id"]

    patched = api.patch(
        f"/catalog/releases/{body['id']}",
        {
            "title": "Pikmin 4 (DE)",
            "region": "de",
            "publisher": {"name": "Nintendo of Europe"},
            "platform_id": str(nds.pk),
            "release_date": "2023-07-21",
        },
    ).json()
    assert patched["title"] == "Pikmin 4 (DE)"
    assert patched["work_title"] == "Pikmin 4"
    assert patched["year"] == 2023
    assert patched["is_released"] is True
    assert patched["platform"]["slug"] == "nds"
    assert patched["release_developers"] == []
    # A release can have studios of its own, besides the game's developers.
    ported = api.patch(
        f"/catalog/releases/{body['id']}", {"release_developers": [{"name": "Panic Button"}]}
    ).json()
    assert [d["name"] for d in ported["release_developers"]] == ["Panic Button"]
    assert ported["title"] == "Pikmin 4 (DE)"  # other fields stay
    panic = api.get("/catalog/companies", {"q": "panic"}).json()[0]
    assert panic["uses"] == 1
    page = api.get(f"/catalog/companies/{panic['id']}").json()
    assert [w["id"] for w in page["works"]] == [body["work_id"]]
    work = api.patch(
        f"/catalog/works/{body['work_id']}",
        {
            "genres": [{"name": "Strategy"}, {"name": "Puzzle"}],
            "developers": [],
            "summary": "Small creatures.",
        },
    ).json()
    assert [g["name"] for g in work["genres"]] == ["Puzzle", "Strategy"]
    assert work["developers"] == []
    assert api.get(f"/catalog/releases/{body['id']}").json()["summary"] == "Small creatures."
    assert len(api.get("/catalog/companies", {"q": "nintendo"}).json()) == 3
    assert {g["name"] for g in api.get("/catalog/genres").json()} >= {"Puzzle", "Strategy"}


def test_create_release_validation(api: Any, switch: Platform) -> None:
    assert (
        api.post("/catalog/releases", {"title": " ", "platform_id": str(switch.pk)}).status_code
        == 400
    )
    unknown = "00000000-0000-0000-0000-000000000000"
    assert api.post("/catalog/releases", {"title": "X", "platform_id": unknown}).status_code == 400
    bad_work = {"title": "X", "platform_id": str(switch.pk), "work_id": unknown}
    assert api.post("/catalog/releases", bad_work).status_code == 400
    bad_code = {"title": "X", "platform_id": str(switch.pk), "barcode": "123"}
    assert api.post("/catalog/releases", bad_code).status_code == 400


def test_barcodes(api: Any, make_release: Callable[..., Release], switch: Platform) -> None:
    one = make_release("One", switch)
    two = make_release("Two", switch)
    assert (
        api.post(f"/catalog/releases/{one.pk}/barcodes", {"code": "4006381333931"}).status_code
        == 200
    )
    # Same code again on the same release is fine, on another one a conflict.
    assert (
        api.post(f"/catalog/releases/{one.pk}/barcodes", {"code": "4006381333931"}).status_code
        == 200
    )
    assert (
        api.post(f"/catalog/releases/{two.pk}/barcodes", {"code": "4006381333931"}).status_code
        == 409
    )
    assert Barcode.objects.get().release == one


def test_cover_upload(api: Any, make_release: Callable[..., Release], switch: Platform) -> None:
    release = make_release("Covered", switch)
    url = f"/api/catalog/releases/{release.pk}/cover"
    upload = SimpleUploadedFile("c.png", _png(), content_type="image/png")
    response = api.client.post(url, {"file": upload})
    assert response.status_code == 200, response.json()
    assert response.json()["cover_url"].startswith("/media/covers/")
    assert response.json()["cover_aspect"] == round(4 / 6, 4)  # the 4×6 test image
    assert response.json()["cover_source"] == "upload"
    # Replacing: the new cover's shape (stored, not just in the answer), a new URL (browsers
    # cache /media), and the old file is gone.
    first = Release.objects.get(pk=release.pk).cover
    buffer = io.BytesIO()
    Image.new("RGB", (10, 5), "red").save(buffer, "PNG")
    again = SimpleUploadedFile("c.png", buffer.getvalue(), content_type="image/png")
    replaced = api.client.post(url, {"file": again}).json()
    assert replaced["cover_aspect"] == 2.0
    assert api.get(f"/catalog/releases/{release.pk}").json()["cover_aspect"] == 2.0
    # Stored, not computed on load (that only happens while the columns are empty).
    stored = Release.objects.values_list("cover_width", "cover_height").get(pk=release.pk)
    assert stored == (10, 5)
    assert replaced["cover_url"] != response.json()["cover_url"]
    assert first.name
    assert not first.storage.exists(first.name)

    not_image = SimpleUploadedFile("c.png", b"hello", content_type="image/png")
    assert api.client.post(url, {"file": not_image}).status_code == 400
    gif = io.BytesIO()
    Image.new("RGB", (2, 2)).save(gif, "GIF")
    wrong_type = SimpleUploadedFile("c.gif", gif.getvalue(), content_type="image/gif")
    assert api.client.post(url, {"file": wrong_type}).status_code == 400


def test_work_cover(
    api: Any, make_release: Callable[..., Release], switch: Platform, library: Any
) -> None:
    """A game can have a general cover of its own: shown for the game and for releases
    (and so copies) without a cover; a release's own cover still wins."""
    bare = make_release("Key Art", switch)
    covered = Release.objects.create(work=bare.work, platform=switch, region="na")
    covered.cover.save("c.png", SimpleUploadedFile("c.png", _png()), save=True)
    copy = library.items.create(release=bare)
    url = f"/api/catalog/works/{bare.work_id}/cover"
    work = api.get(f"/catalog/works/{bare.work_id}").json()
    assert work["has_cover"] is False
    assert work["cover_url"] == covered.cover.url  # the first release cover until then

    buffer = io.BytesIO()
    Image.new("RGB", (16, 9), "blue").save(buffer, "PNG")
    upload = SimpleUploadedFile("k.png", buffer.getvalue(), content_type="image/png")
    work = api.client.post(url, {"file": upload}).json()
    assert work["has_cover"] is True
    assert work["cover_url"].startswith("/media/covers/works/")
    assert work["cover_aspect"] == round(16 / 9, 4)
    releases = {r["id"]: r for r in work["releases"]}
    assert releases[str(bare.pk)]["cover_url"] == work["cover_url"]
    assert releases[str(bare.pk)]["cover_from_game"] is True
    assert releases[str(covered.pk)]["cover_url"] == covered.cover.url
    assert releases[str(covered.pk)]["cover_from_game"] is False
    item = api.get(f"/libraries/{library.pk}/items/{copy.pk}").json()
    assert (item["cover_url"], item["cover_aspect"]) == (work["cover_url"], round(16 / 9, 4))

    stored = Work.objects.get(pk=bare.work_id).cover
    removed = api.client.delete(url).json()
    assert removed["has_cover"] is False
    assert stored.name
    assert not stored.storage.exists(stored.name)
    assert api.get(f"/catalog/releases/{bare.pk}").json()["cover_url"] is None


def test_cover_too_large(
    api: Any, settings: Any, make_release: Callable[..., Release], switch: Platform
) -> None:
    settings.COVER_MAX_MB = 0
    release = make_release("Huge", switch)
    upload = SimpleUploadedFile("c.png", _png(), content_type="image/png")
    response = api.client.post(f"/api/catalog/releases/{release.pk}/cover", {"file": upload})
    assert response.status_code == 400


def test_model_strings(make_release: Callable[..., Release], switch: Platform) -> None:
    release = make_release("Metroid Dread", switch, publisher="Nintendo", genres=("Action",))
    assert str(release) == "Metroid Dread (Nintendo Switch, pal)"
    assert str(release.work) == "Metroid Dread"
    assert str(release.publisher) == "Nintendo"
    assert str(release.work.genres.get()) == "Action"
    assert str(switch) == "Nintendo Switch"
    barcode = Barcode.objects.create(code="4006381333931", release=release)
    assert str(barcode) == "4006381333931"
    assert release.year is None
