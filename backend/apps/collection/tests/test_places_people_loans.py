from typing import Any

from apps.collection.models import Item, Library, Loan, Location, Person


def test_locations(api: Any, library: Library, stocked: dict[str, Item]) -> None:
    path = f"/libraries/{library.pk}/locations"
    room = api.post(path, {"name": "Wohnzimmer", "kind": "room"}).json()
    shelf = api.post(path, {"name": "Regal", "kind": "shelf", "parent_id": room["id"]}).json()
    box = api.post(path, {"name": "Box A", "kind": "box", "parent_id": shelf["id"]}).json()
    assert box["path"] == "Wohnzimmer › Regal › Box A"
    assert api.post(path, {"name": " "}).status_code == 400
    assert (
        api.post(
            path, {"name": "X", "parent_id": "00000000-0000-0000-0000-000000000000"}
        ).status_code
        == 400
    )

    stocked["mk8"].location_id = box["id"]
    stocked["mk8"].save()
    listed = api.get(path).json()
    assert [loc["path"] for loc in listed] == [
        "Wohnzimmer",
        "Wohnzimmer › Regal",
        "Wohnzimmer › Regal › Box A",
    ]
    assert listed[2]["item_count"] == 1

    # No cycles: a room can't move into its own box.
    assert api.patch(f"{path}/{room['id']}", {"parent_id": box["id"]}).status_code == 400
    moved = api.patch(f"{path}/{box['id']}", {"parent_id": room["id"], "name": "Kiste"}).json()
    assert moved["path"] == "Wohnzimmer › Kiste"
    assert api.patch(f"{path}/{box['id']}", {"parent_id": None}).json()["path"] == "Kiste"
    assert api.delete(f"{path}/{room['id']}").status_code == 204
    assert Location.objects.count() == 1
    assert str(Location.objects.get()) == "Kiste"


def test_people(api: Any, library: Library) -> None:
    path = f"/libraries/{library.pk}/people"
    lena = api.post(path, {"name": "Lena", "email": "lena@example.com"}).json()
    assert api.post(path, {"name": ""}).status_code == 400
    assert (
        api.patch(f"{path}/{lena['id']}", {"notes": "Schwester", "email": None}).json()["notes"]
        == "Schwester"
    )
    assert [p["name"] for p in api.get(path).json()] == ["Lena"]
    assert str(Person.objects.get()) == "Lena"
    assert api.delete(f"{path}/{lena['id']}").status_code == 204


def test_loans(api: Any, library: Library, stocked: dict[str, Item]) -> None:
    path = f"/libraries/{library.pk}/loans"
    item = stocked["zelda"]
    lent = api.post(
        path,
        {"item_id": str(item.pk), "borrower_name": "Max", "due_on": "2000-01-01"},
    )
    assert lent.status_code == 201, lent.json()
    loan = lent.json()
    assert loan["borrower"]["name"] == "Max"
    assert loan["overdue"] is True
    assert loan["item_title"] == "Zelda: Breath of the Wild"
    assert loan["platform"] == "Switch"

    # Already lent out; and the item shows the open loan.
    assert api.post(path, {"item_id": str(item.pk), "borrower_name": "Max"}).status_code == 409
    items = f"/libraries/{library.pk}/items/{item.pk}"
    assert api.get(items).json()["active_loan"]["borrower"]["name"] == "Max"
    tree = api.get(f"/libraries/{library.pk}/tree", {"group_by": "loan.to"}).json()
    assert [n["label"] for n in tree["nodes"]] == ["Max", ""]
    people = api.get(f"/libraries/{library.pk}/people").json()
    assert people[0]["open_loans"] == 1
    assert api.delete(f"/libraries/{library.pk}/people/{people[0]['id']}").status_code == 409

    assert len(api.get(path, {"open": True}).json()) == 1
    returned = api.post(f"{path}/{loan['id']}/return", {"returned_on": "2024-05-01"}).json()
    assert returned["returned_on"] == "2024-05-01"
    assert returned["overdue"] is False
    assert api.post(f"{path}/{loan['id']}/return", {}).status_code == 409
    assert api.get(path, {"open": True}).json() == []
    assert len(api.get(path, {"item": str(item.pk)}).json()) == 1

    max_id = people[0]["id"]
    again = api.post(path, {"item_id": str(item.pk), "borrower_id": max_id}).json()
    assert again["returned_on"] is None
    assert (
        str(Loan.objects.get(pk=again["id"]))
        == "Zelda: Breath of the Wild (Nintendo Switch, pal) → Max"
    )
    assert api.delete(f"{path}/{again['id']}").status_code == 204


def test_loan_validation(api: Any, library: Library, stocked: dict[str, Item]) -> None:
    path = f"/libraries/{library.pk}/loans"
    item = str(stocked["mk8"].pk)
    unknown = "00000000-0000-0000-0000-000000000000"
    assert api.post(path, {"item_id": unknown, "borrower_name": "A"}).status_code == 400
    assert api.post(path, {"item_id": item, "borrower_id": unknown}).status_code == 400
    assert api.post(path, {"item_id": item}).status_code == 400


def test_overviews(api: Any, other_api: Any, library: Library) -> None:
    path = f"/libraries/{library.pk}/overviews"
    created = api.post(
        path,
        {
            "name": "Plattform › Publisher › Jahr",
            "group_by": ["platform.name", "publisher.name", "release.year"],
        },
    )
    assert created.status_code == 201
    overview = created.json()
    assert overview["layout"] == "grid"
    assert api.post(path, {"name": "x", "group_by": ["colour"]}).status_code == 400
    assert api.post(path, {"name": "x", "sort": "random"}).status_code == 400
    assert api.post(path, {"name": " "}).status_code == 400
    assert api.post(path, {"name": "x", "fields": {"grid": ["Bad Key"]}}).status_code == 400
    assert (
        api.post(path, {"name": "x", "fields": {"grid": ["release.year"] * 41}}).status_code == 400
    )
    assert api.post(path, {"name": "x", "fields": {"poster": ["release.year"]}}).status_code == 400
    patched = api.patch(
        f"{path}/{overview['id']}",
        {
            "layout": "table",
            "filters": ["copy.status=owned", "game.title~A*"],
            "match": "any",
            "fields": {"table": ["release.number", "location.box"], "detail": ["game.series"]},
            "name": None,
        },
    ).json()
    assert patched["layout"] == "table"
    assert patched["fields"] == {
        "table": ["release.number", "location.box"],
        "detail": ["game.series"],
    }
    assert patched["filters"] == ["copy.status=owned", "game.title~A*"]
    assert patched["match"] == "any"
    assert patched["section"] == ""
    sectioned = api.patch(f"{path}/{overview['id']}", {"section": "copy.added"}).json()
    assert sectioned["section"] == "copy.added"
    cleared = api.patch(f"{path}/{overview['id']}", {"section": ""}).json()
    assert cleared["section"] == ""
    assert api.patch(f"{path}/{overview['id']}", {"section": "colour"}).status_code == 400
    assert api.post(path, {"name": "x", "filters": ["game.title?=x"]}).status_code == 400
    assert [o["name"] for o in api.get(path).json()] == ["Plattform › Publisher › Jahr"]
    assert other_api.get(path).status_code == 404
    assert api.delete(f"{path}/{overview['id']}").status_code == 204
