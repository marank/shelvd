from typing import Any

from apps.collection.models import Item, Library, Location, Person
from apps.sharing.models import CustomList, ListEntry


def test_lists(api: Any, other_api: Any, library: Library, stocked: dict[str, Item]) -> None:
    created = api.post("/lists", {"name": "Ausleihen?", "description": "Für Bob"})
    assert created.status_code == 201
    custom = created.json()
    assert api.post("/lists", {"name": ""}).status_code == 400
    path = f"/lists/{custom['id']}"
    mk8 = stocked["mk8"]
    entry = api.post(
        f"{path}/entries", {"release_id": str(mk8.release_id), "item_id": str(mk8.pk), "note": "!"}
    )
    assert entry.status_code == 201
    assert entry.json()["position"] == 1
    sonic = api.post(f"{path}/entries", {"release_id": str(stocked["sonic"].release_id)}).json()
    assert sonic["position"] == 2
    assert api.post(f"{path}/entries", {"release_id": str(mk8.release_id)}).status_code == 409
    unknown = "00000000-0000-0000-0000-000000000000"
    assert api.post(f"{path}/entries", {"release_id": unknown}).status_code == 400
    wrong_item = {"release_id": str(stocked["zelda"].release_id), "item_id": str(mk8.pk)}
    assert api.post(f"{path}/entries", wrong_item).status_code == 400

    moved = api.patch(f"{path}/entries/{sonic['id']}", {"position": 0, "note": None}).json()
    assert moved["position"] == 0
    titles = [e["release"]["title"] for e in api.get(f"{path}/entries").json()]
    assert titles == ["Sonic Rush", "Mario Kart 8 Deluxe"]

    assert api.get("/lists").json()[0]["entry_count"] == 2
    assert api.patch(path, {"name": "Leihliste", "description": None}).json()["name"] == "Leihliste"
    assert api.get(path).json()["name"] == "Leihliste"
    # Lists are private to their owner.
    assert other_api.get(path).status_code == 404
    assert other_api.get("/lists").json() == []

    token = api.post(f"{path}/public-link").json()["public_token"]
    public = other_api.get(f"/public/lists/{token}").json()
    assert public["owner"] == "alice"
    assert len(public["entries"]) == 2
    assert api.delete(f"{path}/public-link").json()["public_token"] is None
    assert other_api.get(f"/public/lists/{token}").status_code == 404

    assert api.delete(f"{path}/entries/{sonic['id']}").status_code == 204
    assert str(ListEntry.objects.get()) == "Leihliste: Mario Kart 8 Deluxe (Nintendo Switch, pal)"
    assert str(CustomList.objects.get()) == "Leihliste"
    assert api.delete(path).status_code == 204


def test_public_library(anon_api: Any, library: Library, stocked: dict[str, Item]) -> None:
    assert anon_api.get("/public/libraries/nope").status_code == 404
    library.public_token = "tok"
    library.save()
    stocked["mk8"].owner = Person.objects.create(library=library, name="Secret Person")
    stocked["mk8"].location = Location.objects.create(library=library, name="Secret Room")
    stocked["mk8"].purchase_price = 10
    stocked["mk8"].save()

    info = anon_api.get("/public/libraries/tok").json()
    assert info == {"name": "Games", "description": "", "owner": "alice", "item_count": 3}
    tree = anon_api.get(
        "/public/libraries/tok/tree",
        {"group_by": ["owner.name", "platform.name"], "filter": "owner.name:x"},
    ).json()
    # Private fields are ignored, not answered.
    assert tree["group_by"] == ["platform.name"]
    assert tree["total"] == 3
    items = anon_api.get("/public/libraries/tok/items", {"limit": 2}).json()
    assert items["count"] == 3
    assert len(items["items"]) == 2
    assert set(items["items"][0]) == {
        "id",
        "title",
        "cover_url",
        "cover_aspect",
        "release",
        "format",
        "status",
        "completeness",
    }
    assert "Secret" not in str(anon_api.get("/public/libraries/tok/items").content)
