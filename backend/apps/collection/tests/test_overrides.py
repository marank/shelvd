import io
from pathlib import Path
from typing import Any

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.collection.models import Item, Library
from apps.collection.services.items import delete_item


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 6), "blue").save(buffer, "PNG")
    return buffer.getvalue()


def test_title_and_cover_override(api: Any, library: Library, stocked: dict[str, Item]) -> None:
    item = stocked["sonic"]
    path = f"/libraries/{library.pk}/items/{item.pk}"
    renamed = api.patch(path, {"title_override": "Sonic Rush (Mein Exemplar)"}).json()
    assert renamed["title"] == "Sonic Rush (Mein Exemplar)"
    # The copy shows its own title; the catalog stays untouched.
    assert renamed["release"]["title"] == "Sonic Rush (Mein Exemplar)"
    assert renamed["overrides"] == ["title"]
    assert api.get(f"/catalog/releases/{item.release_id}").json()["title"] == "Sonic Rush"
    titles = [i["title"] for i in api.get(f"/libraries/{library.pk}/items").json()["items"]]
    assert "Sonic Rush (Mein Exemplar)" in titles
    assert api.get(f"/libraries/{library.pk}/items", {"q": "exemplar"}).json()["count"] == 1

    upload = SimpleUploadedFile("c.png", _png(), content_type="image/png")
    covered = api.client.post(f"/api{path}/cover", {"file": upload})
    assert covered.status_code == 200, covered.json()
    body = covered.json()
    assert body["has_cover_override"] is True
    assert body["cover_aspect"] == round(4 / 6, 4)
    assert body["cover_url"].startswith("/media/item-covers/")
    assert body["release"]["cover_url"] == body["cover_url"]
    assert body["overrides"] == ["title", "cover"]
    # Replacing: the new shape is stored, under a new URL; the old file is gone.
    first = Item.objects.get(pk=item.pk).cover_override
    buffer = io.BytesIO()
    Image.new("RGB", (10, 5), "red").save(buffer, "PNG")
    wide = SimpleUploadedFile("w.png", buffer.getvalue(), content_type="image/png")
    replaced = api.client.post(f"/api{path}/cover", {"file": wide}).json()
    assert replaced["cover_aspect"] == 2.0
    assert api.get(path).json()["cover_aspect"] == 2.0
    stored = Item.objects.values_list("cover_override_width", "cover_override_height")
    assert stored.get(pk=item.pk) == (10, 5)
    assert replaced["cover_url"] != body["cover_url"]
    assert first.name
    assert not first.storage.exists(first.name)
    reset = api.delete(f"{path}/cover").json()
    assert reset["has_cover_override"] is False
    assert reset["cover_url"] is None
    assert reset["cover_aspect"] is None


def test_edition_region_and_date_overrides(
    api: Any, library: Library, stocked: dict[str, Item]
) -> None:
    item = stocked["sonic"]
    path = f"/libraries/{library.pk}/items/{item.pk}"
    changed = api.patch(
        path,
        {
            "edition_override": " Classics ",
            "region_override": "jp",
            "release_precision_override": "month",
            "release_date_override": "1999-05-17",
        },
    ).json()
    shown = changed["release"]
    assert (shown["edition"], shown["region"], shown["release_date"]) == (
        "Classics",
        "jp",
        "1999-05-01",  # the month's first day, like a release's
    )
    assert (shown["release_precision"], shown["year"], shown["is_released"]) == (
        "month",
        1999,
        True,
    )
    assert changed["overrides"] == ["edition", "region", "release_date"]
    assert changed["region_override"] == "jp"
    # Lists, groups, sorting and filters see what the copy shows.
    items = f"/libraries/{library.pk}/items"
    assert api.get(items, {"filter": "release.region:jp"}).json()["count"] == 1
    years = api.get(f"/libraries/{library.pk}/tree", {"group_by": "release.year"}).json()
    assert "1999" in [n["label"] for n in years["nodes"]]
    oldest = api.get(items, {"sort": "release.date"}).json()["items"][0]
    assert oldest["id"] == str(item.pk)
    # Other untouched fields don't count; a single one resets with "".
    kept = api.patch(path, {"notes": "x", "region_override": ""}).json()
    assert kept["overrides"] == ["edition", "release_date"]
    assert kept["release"]["release_precision"] == "month"
    undated = api.patch(path, {"release_precision_override": ""}).json()
    assert undated["release"]["year"] == 2005
    assert undated["release_date_override"] is None
    # A window keeps its end; a TBA has no year.
    window = api.patch(
        path,
        {"release_precision_override": "window", "release_date_override": "2030-01-01",
         "release_date_end_override": "2030-03-31"},
    ).json()  # fmt: skip
    assert window["release_date_end_override"] == "2030-03-31"
    assert window["release"]["is_released"] is False
    assert api.patch(path, {"release_precision_override": "tba"}).json()["release"]["year"] is None

    reset = api.post(f"{path}/reset").json()
    assert reset["overrides"] == []
    assert reset["release"]["edition"] == ""
    assert Item.objects.get(pk=item.pk).release.edition == ""


def test_viewers_cannot_override(
    other_api: Any, library: Library, stocked: dict[str, Item], other: Any
) -> None:
    from apps.collection.models import LibraryMember, Role

    LibraryMember.objects.create(library=library, user=other, role=Role.VIEWER)
    path = f"/libraries/{library.pk}/items/{stocked['sonic'].pk}"
    assert other_api.patch(path, {"edition_override": "X"}).status_code == 403
    assert other_api.post(f"{path}/reset").status_code == 403


def test_items_of_one_work(api: Any, library: Library, stocked: dict[str, Item]) -> None:
    work = stocked["zelda"].release.work_id
    found = api.get(f"/libraries/{library.pk}/items", {"work": str(work)}).json()
    assert [i["id"] for i in found["items"]] == [str(stocked["zelda"].pk)]


def test_work_page(api: Any, stocked: dict[str, Item]) -> None:
    work = stocked["zelda"].release.work
    body = api.get(f"/catalog/works/{work.pk}").json()
    assert body["title"] == "Zelda: Breath of the Wild"
    # With ids, for the edit form's pickers.
    assert [g["name"] for g in body["genres"]] == ["Adventure", "RPG"]
    assert [d["name"] for d in body["developers"]] == ["Nintendo EPD"]
    assert all(g["id"] for g in body["genres"])
    assert [r["platform"]["slug"] for r in body["releases"]] == ["switch"]
    assert body["cover_url"] is None
    assert api.patch(f"/catalog/works/{work.pk}", {"title": " "}).status_code == 400
    renamed = api.patch(
        f"/catalog/works/{work.pk}", {"title": "Zelda BotW", "first_release_date": "2017-03-03"}
    ).json()
    assert renamed["title"] == "Zelda BotW"
    assert renamed["first_release_date"] == "2017-03-03"
    assert api.get("/catalog/works/00000000-0000-0000-0000-000000000000").status_code == 404


def _covered(api: Any, library: Library, item: Item) -> Path:
    upload = SimpleUploadedFile("c.png", _png(), content_type="image/png")
    path = f"/api/libraries/{library.pk}/items/{item.pk}/cover"
    assert api.client.post(path, {"file": upload}).status_code == 200
    file = Path(Item.objects.get(pk=item.pk).cover_override.path)
    assert file.exists()
    return file


def test_deleting_a_copy_removes_its_cover(
    api: Any, library: Library, stocked: dict[str, Item], django_capture_on_commit_callbacks: Any
) -> None:
    item = stocked["sonic"]
    file = _covered(api, library, item)
    with django_capture_on_commit_callbacks(execute=True):
        assert api.delete(f"/libraries/{library.pk}/items/{item.pk}").status_code == 204
    assert not Item.objects.filter(pk=item.pk).exists()
    assert not file.exists()


def test_deleting_a_library_removes_the_covers_of_its_copies(
    api: Any, library: Library, stocked: dict[str, Item], django_capture_on_commit_callbacks: Any
) -> None:
    files = [_covered(api, library, stocked[key]) for key in ("sonic", "mk8")]
    with django_capture_on_commit_callbacks(execute=True):
        assert api.delete(f"/libraries/{library.pk}").status_code == 204
    assert not Library.objects.filter(pk=library.pk).exists()
    assert not any(file.exists() for file in files)


def test_a_rolled_back_deletion_keeps_the_cover(
    api: Any, library: Library, stocked: dict[str, Item], django_capture_on_commit_callbacks: Any
) -> None:
    item = stocked["sonic"]
    file = _covered(api, library, item)
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        delete_item(Item.objects.get(pk=item.pk))
    # Nothing is removed before the deletion is committed.
    assert len(callbacks) == 1
    assert file.exists()
