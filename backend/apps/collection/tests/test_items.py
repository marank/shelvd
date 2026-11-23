from collections.abc import Callable
from typing import Any

from apps.accounts.models import User
from apps.catalog.models import Barcode, Company, Platform, Release
from apps.collection.models import Item, Library, Location, Person


def test_item_crud(
    api: Any, library: Library, make_release: Callable[..., Release], switch: Platform
) -> None:
    release = make_release("Splatoon 3", switch, year=2022, publisher="Nintendo")
    room = Location.objects.create(library=library, name="Office", kind="room")
    person = Person.objects.create(library=library, name="Lena")
    path = f"/libraries/{library.pk}/items"
    created = api.post(
        path,
        {
            "release_id": str(release.pk),
            "condition": "good",
            "completeness": "complete",
            "location_id": str(room.pk),
            "owner_id": str(person.pk),
            "purchase_price": "49.99",
            "acquired_on": "2022-09-09",
        },
    )
    assert created.status_code == 201, created.json()
    item = created.json()
    assert item["release"]["title"] == "Splatoon 3"
    assert item["location"]["path"] == "Office"
    assert item["owner"]["name"] == "Lena"
    assert item["play_status"] is None
    assert item["active_loan"] is None

    updated = api.patch(
        f"{path}/{item['id']}",
        {"play_status": "playing", "location_id": None, "condition": None, "notes": "Gift"},
    ).json()
    assert updated["play_status"] == "playing"
    assert updated["location"] is None
    assert updated["condition"] is None
    assert updated["notes"] == "Gift"
    assert (
        api.patch(f"{path}/{item['id']}", {"format": None, "status": "sold"}).json()["status"]
        == "sold"
    )
    assert api.get(f"{path}/{item['id']}").json()["notes"] == "Gift"
    assert api.delete(f"{path}/{item['id']}").status_code == 204
    assert api.get(f"{path}/{item['id']}").status_code == 404


def test_item_validation(
    api: Any, library: Library, make_release: Callable[..., Release], switch: Platform
) -> None:
    release = make_release("Kirby", switch)
    foreign = Library.objects.create(name="Other", owner=library.owner)
    elsewhere = Location.objects.create(library=foreign, name="Attic")
    stranger = Person.objects.create(library=foreign, name="Tom")
    path = f"/libraries/{library.pk}/items"
    unknown = "00000000-0000-0000-0000-000000000000"
    assert api.post(path, {"release_id": unknown}).status_code == 400
    base = {"release_id": str(release.pk)}
    assert api.post(path, {**base, "location_id": str(elsewhere.pk)}).status_code == 400
    assert api.post(path, {**base, "owner_id": str(stranger.pk)}).status_code == 400
    assert api.post(path, {**base, "status": "lost"}).status_code == 422


def test_search_filters_sort_pages(api: Any, library: Library, stocked: dict[str, Item]) -> None:
    path = f"/libraries/{library.pk}/items"

    def titles(response: Any) -> list[str]:
        return [i["release"]["title"] for i in response.json()["items"]]

    assert titles(api.get(path)) == [
        "Mario Kart 8 Deluxe",
        "Sonic Rush",
        "Zelda: Breath of the Wild",
    ]
    assert titles(api.get(path, {"q": "nintendo switch"})) == [
        "Mario Kart 8 Deluxe",
        "Zelda: Breath of the Wild",
    ]
    assert titles(api.get(path, {"q": "signed"})) == ["Zelda: Breath of the Wild"]
    assert titles(api.get(path, {"q": "rpg"})) == ["Zelda: Breath of the Wild"]
    Barcode.objects.create(code="4006381333931", release=stocked["sonic"].release)
    assert titles(api.get(path, {"q": "4006381333931"})) == ["Sonic Rush"]

    sega = str(stocked["sonic"].release.publisher_id)
    assert titles(api.get(path, {"filter": f"publisher.name:{sega}"})) == ["Sonic Rush"]
    assert titles(api.get(path, {"filter": ["release.year:2017", "game.genres:none"]})) == []
    assert api.get(path, {"filter": "nonsense"}).status_code == 400
    assert api.get(path, {"filter": "colour:red"}).status_code == 400

    assert titles(api.get(path, {"sort": "release.year"}))[0] == "Sonic Rush"
    assert titles(api.get(path, {"sort": "-platform.name"}))[-1] == "Sonic Rush"
    assert len(titles(api.get(path, {"sort": "copy.added"}))) == 3
    assert len(titles(api.get(path, {"sort": "copy.acquired"}))) == 3
    page = api.get(path, {"limit": 1, "offset": 1}).json()
    assert page["count"] == 3
    assert [i["release"]["title"] for i in page["items"]] == ["Sonic Rush"]


def test_tree(api: Any, library: Library, stocked: dict[str, Item]) -> None:
    path = f"/libraries/{library.pk}/tree"
    tree = api.get(path, {"group_by": ["platform.name", "publisher.name", "release.year"]}).json()
    assert tree["total"] == 3
    platforms = [(n["label"], n["count"]) for n in tree["nodes"]]
    assert platforms == [("Nintendo DS", 1), ("Nintendo Switch", 2)]
    switch = tree["nodes"][1]
    assert [(n["label"], n["count"]) for n in switch["children"]] == [("Nintendo", 2)]
    assert switch["children"][0]["children"][0]["label"] == "2017"
    # Multi-valued fields put an item into several groups.
    genres = api.get(path, {"group_by": "game.genres"}).json()["nodes"]
    assert [n["label"] for n in genres] == ["Adventure", "Platformer", "Racing", "RPG"]
    assert api.get(path, {"group_by": "colour"}).status_code == 400
    filtered = api.get(path, {"group_by": "release.decade", "q": "sonic"}).json()
    assert [(n["label"], n["count"]) for n in filtered["nodes"]] == [("2000s", 1)]


def test_every_group_field(api: Any, library: Library, stocked: dict[str, Item]) -> None:
    from apps.collection.selectors.grouping import FIELDS

    shelf = Location.objects.create(
        library=library, name="Shelf", parent=Location.objects.create(library=library, name="Room")
    )
    stocked["mk8"].location = shelf
    stocked["mk8"].condition = "good"
    stocked["mk8"].save()
    path = f"/libraries/{library.pk}/tree"
    for field in FIELDS:
        response = api.get(path, {"group_by": field})
        assert response.status_code == 200, field
        assert sum(n["count"] for n in response.json()["nodes"]) >= 3, field
    rooms = api.get(path, {"group_by": "location.room"}).json()["nodes"]
    assert [n["label"] for n in rooms] == ["Room", ""]
    letters = api.get(path, {"group_by": "game.letter"}).json()["nodes"]
    assert [n["label"] for n in letters] == ["M", "S", "Z"]
    stocked["mk8"].release.developers.add(Company.objects.create(name="Bandai Namco"))
    studios = api.get(path, {"group_by": "release.developers"}).json()["nodes"]
    assert [n["label"] for n in studios] == ["Bandai Namco", ""]


def test_group_by_box_and_shelf(api: Any, library: Library, stocked: dict[str, Item]) -> None:
    room = Location.objects.create(library=library, name="Office", kind="room")
    shelf = Location.objects.create(library=library, name="Left", kind="shelf", parent=room)
    box = Location.objects.create(library=library, name="Box A", kind="box", parent=shelf)
    loose = Location.objects.create(library=library, name="Box B", kind="box")
    stocked["mk8"].location = box
    stocked["mk8"].save()
    stocked["zelda"].location = loose
    stocked["zelda"].save()
    path = f"/libraries/{library.pk}/tree"
    boxes = api.get(path, {"group_by": "location.box"}).json()["nodes"]
    assert [(n["label"], n["count"]) for n in boxes] == [("Box A", 1), ("Box B", 1), ("", 1)]
    # A copy in a box on a shelf counts for that shelf too.
    shelves = api.get(path, {"group_by": "location.shelf"}).json()["nodes"]
    assert [(n["label"], n["count"]) for n in shelves] == [("Left", 1), ("", 2)]


def test_item_by_id_alone(api: Any, library: Library, stocked: dict[str, Item]) -> None:
    item = stocked["sonic"]
    body = api.get(f"/items/{item.pk}").json()
    assert body["id"] == str(item.pk)
    assert body["library_id"] == str(library.pk)
    # Copies of libraries you can't see look like unknown ones.
    other = Library.objects.create(name="Other", owner=User.objects.create(username="someone-else"))
    foreign = Item.objects.create(library=other, release=item.release)
    assert api.get(f"/items/{foreign.pk}").status_code == 404
    assert api.get("/items/01a19938-0000-7000-8000-000000000000").status_code == 404


def test_sections(api: Any, library: Library, stocked: dict[str, Item]) -> None:
    path = f"/libraries/{library.pk}/items"
    body = api.get(path, {"section": "platform.name", "sort": "game.title"}).json()
    sections = [(s["label"], s["count"], s["start"]) for s in body["sections"]]
    assert sections == [("Nintendo DS", 1, 0), ("Nintendo Switch", 2, 1)]
    assert body["count"] == 3
    # Within a section the list keeps its sort.
    titles = [i["release"]["title"] for i in body["items"]]
    assert titles[0] == "Sonic Rush"
    assert titles[1:] == sorted(titles[1:])
    # Paging walks the rows; the headings always cover the whole list.
    page = api.get(path, {"section": "platform.name", "limit": 1, "offset": 2}).json()
    assert len(page["items"]) == 1
    assert len(page["sections"]) == 2
    # An item with several genres is listed under each.
    genres = api.get(path, {"section": "game.genres"}).json()
    assert genres["count"] == sum(s["count"] for s in genres["sections"]) > 3
    assert api.get(path).json()["sections"] == []
    assert api.get(path, {"section": "colour"}).status_code == 400


def test_sections_by_month(api: Any, library: Library, stocked: dict[str, Item]) -> None:
    from datetime import date

    stocked["mk8"].acquired_on = date(2024, 3, 9)
    stocked["mk8"].save()
    stocked["zelda"].acquired_on = date(2025, 1, 2)
    stocked["zelda"].save()
    path = f"/libraries/{library.pk}/items"
    body = api.get(path, {"section": "copy.acquired"}).json()
    # Newest first, copies without a date last.
    assert [s["key"] for s in body["sections"]] == ["2025-01", "2024-03", "none"]
    added = api.get(path, {"section": "copy.added"}).json()["sections"]
    assert len(added) == 1
    assert added[0]["count"] == 3
    folder = api.get(path, {"filter": "copy.acquired:2024-03"}).json()
    assert [i["id"] for i in folder["items"]] == [str(stocked["mk8"].pk)]


def test_owned_releases(api: Any, library: Library, stocked: dict[str, Item], user: Any) -> None:
    """Catalog pages and the add dialog mark what the library has: owned copies per release
    (with its game), sold ones don't count."""
    item = next(iter(stocked.values()))
    Item.objects.create(library=library, release=item.release)
    Item.objects.create(library=library, release=item.release, status="sold")
    rows = api.get(f"/libraries/{library.pk}/owned").json()
    owned = {o["release_id"]: o for o in rows}
    assert owned[str(item.release_id)] == {
        "release_id": str(item.release_id),
        "work_id": str(item.release.work_id),
        "copies": 2,
    }
    assert len(owned) == len({i.release_id for i in stocked.values()})
    other = Library.objects.create(name="Not mine", owner=User.objects.create(username="x"))
    assert api.get(f"/libraries/{other.pk}/owned").status_code == 404
