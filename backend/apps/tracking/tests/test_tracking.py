import datetime
from collections.abc import Callable
from typing import Any

from apps.accounts.models import User
from apps.catalog.models import Platform, Release
from apps.collection.models import Item, Library, LibraryMember, Location
from apps.tracking.models import Tracking


def test_track_preorder_and_take_over(
    api: Any,
    other_api: Any,
    other: User,
    library: Library,
    make_release: Callable[..., Release],
    switch: Platform,
) -> None:
    release = make_release("Metroid Prime 4", switch)
    release.release_precision = "quarter"
    release.release_date = datetime.date(2099, 10, 1)
    release.save()

    created = api.post(
        "/watchlist",
        {
            "release_id": str(release.pk),
            "status": "preordered",
            "library_id": str(library.pk),
            "shop": "Media Markt",
            "price": "59.99",
            "ordered_on": "2026-10-01",
        },
    )
    assert created.status_code == 201, created.json()
    tracking = created.json()
    assert tracking["is_mine"] is True
    assert tracking["release"]["release_precision"] == "quarter"
    assert tracking["release"]["is_released"] is False
    assert tracking["library"]["name"] == "Games"
    duplicate = {"release_id": str(release.pk)}
    assert api.post("/watchlist", duplicate).status_code == 409
    unknown = "00000000-0000-0000-0000-000000000000"
    assert api.post("/watchlist", {"release_id": unknown}).status_code == 400

    # Not in the library itself.
    assert api.get(f"/libraries/{library.pk}/items").json()["count"] == 0

    # Others see it only through the target library, read-only.
    assert other_api.get("/watchlist").json() == []
    LibraryMember.objects.create(library=library, user=other, role="editor")
    seen = other_api.get("/watchlist").json()
    assert [t["user"] for t in seen] == ["alice"]
    assert seen[0]["is_mine"] is False
    assert other_api.get(f"/watchlist/{tracking['id']}").status_code == 200
    assert other_api.patch(f"/watchlist/{tracking['id']}", {"status": "bought"}).status_code == 404
    assert other_api.get("/watchlist", {"mine": True}).json() == []

    path = f"/watchlist/{tracking['id']}"
    patched = api.patch(path, {"status": "bought", "price": None, "library_id": None}).json()
    assert patched["status"] == "bought"
    assert patched["price"] is None
    assert patched["library"] is None
    api.patch(path, {"price": "49.99", "notes": "Steelbook", "shop": None})
    assert len(api.get("/watchlist", {"work": str(release.work_id)}).json()) == 1
    assert api.get("/watchlist", {"library": str(library.pk)}).json() == []

    box = Location.objects.create(library=library, name="Box")
    taken = api.post(
        f"{path}/take-over",
        {"library_id": str(library.pk), "location_id": str(box.pk), "notes": "Day one"},
    )
    assert taken.status_code == 201, taken.json()
    item = taken.json()
    assert item["purchase_price"] == "49.99"
    assert item["acquired_on"] == "2026-10-01"
    assert item["notes"] == "Steelbook\nDay one"
    assert item["location"]["name"] == "Box"
    assert not Tracking.objects.exists()
    assert Item.objects.filter(library=library).count() == 1


def test_take_over_needs_edit_rights(
    api: Any, other: User, make_release: Callable[..., Release], switch: Platform
) -> None:
    release = make_release("Kirby", switch)
    foreign = Library.objects.create(name="Bob's", owner=other)
    tracking = api.post("/watchlist", {"release_id": str(release.pk)}).json()
    target = {"library_id": str(foreign.pk)}
    assert api.post(f"/watchlist/{tracking['id']}/take-over", target).status_code == 404
    assert (
        api.post(
            "/watchlist",
            {"release_id": str(make_release("X", switch).pk), "library_id": str(foreign.pk)},
        ).status_code
        == 404
    )
    assert api.delete(f"/watchlist/{tracking['id']}").status_code == 204
    assert str(Tracking.objects.count()) == "0"


def test_str(user: User, make_release: Callable[..., Release], switch: Platform) -> None:
    tracking = Tracking.objects.create(user=user, release=make_release("Y", switch))
    assert str(tracking) == "alice: Y (Nintendo Switch, pal) (watching)"


def test_owned_in_visible_libraries(
    api: Any,
    user: User,
    other: User,
    library: Library,
    make_release: Callable[..., Release],
    switch: Platform,
) -> None:
    """An entry knows where its release already sits, so it isn't offered to take over again."""
    release = make_release("Marvel's Wolverine", switch)
    tracking = api.post("/watchlist", {"release_id": str(release.pk)}).json()
    assert tracking["owned_in"] == []

    hidden = Library.objects.create(name="Bob's", owner=other)
    Item.objects.create(library=hidden, release=release)  # not visible to alice
    Item.objects.create(library=library, release=release, status="sold")  # gone again
    assert api.get(f"/watchlist/{tracking['id']}").json()["owned_in"] == []

    shelf = Library.objects.create(name="Archive", owner=user)
    Item.objects.create(library=shelf, release=release)
    Item.objects.create(library=library, release=release)
    Item.objects.create(library=library, release=release)
    expected = [{"id": str(shelf.pk), "name": "Archive"}, {"id": str(library.pk), "name": "Games"}]
    assert api.get(f"/watchlist/{tracking['id']}").json()["owned_in"] == expected
    assert api.get("/watchlist").json()[0]["owned_in"] == expected
