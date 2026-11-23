from decimal import Decimal
from typing import Any

import pytest
from ninja.errors import HttpError

from apps.collection.models import Item, Library, Location
from apps.collection.selectors.sorting import SORT_KEYS, parse_sort


def titles(api: Any, library: Library, sort: str, **params: Any) -> list[str]:
    response = api.get(f"/libraries/{library.pk}/items", {"sort": sort, **params})
    assert response.status_code == 200, response.json()
    return [item["title"] for item in response.json()["items"]]


def test_every_key_sorts(api: Any, library: Library, stocked: dict[str, Item]) -> None:
    for key in SORT_KEYS:
        assert len(titles(api, library, key)) == 3, key
        assert len(titles(api, library, f"-{key}")) == 3, key


def test_levels_directions_and_empty_last(
    api: Any, library: Library, stocked: dict[str, Item]
) -> None:
    box = Location.objects.create(library=library, name="Box A", kind="box")
    stocked["mk8"].location = box
    stocked["mk8"].current_value = Decimal(50)
    stocked["mk8"].save()
    stocked["sonic"].current_value = Decimal(20)
    stocked["sonic"].save()
    # Year descending, then title: 2017 (Mario, Zelda) before 2005.
    assert titles(api, library, "-release.year,game.title") == [
        "Mario Kart 8 Deluxe",
        "Zelda: Breath of the Wild",
        "Sonic Rush",
    ]
    # Zelda has no value: last in both directions.
    assert titles(api, library, "copy.value")[-1] == "Zelda: Breath of the Wild"
    assert titles(api, library, "-copy.value") == [
        "Mario Kart 8 Deluxe",
        "Sonic Rush",
        "Zelda: Breath of the Wild",
    ]
    # Copies without a box after the one in a box; ties by title.
    assert titles(api, library, "location.box") == [
        "Mario Kart 8 Deluxe",
        "Sonic Rush",
        "Zelda: Breath of the Wild",
    ]
    assert api.get(f"/libraries/{library.pk}/items", {"sort": "colour"}).status_code == 400


def test_parse_sort() -> None:
    assert parse_sort("location.box,-release.number,") == [
        ("location.box", False),
        ("release.number", True),
    ]
    assert parse_sort("location.box,owner.name,game.title", allowed={"game.title"}) == [
        ("game.title", False)
    ]
    with pytest.raises(HttpError):
        parse_sort(",".join(["game.title"] * 6))


def test_views_store_sort_levels(api: Any, library: Library) -> None:
    path = f"/libraries/{library.pk}/overviews"
    created = api.post(path, {"name": "Boxes", "sort": "location.box,-release.number"})
    assert created.json()["sort"] == "location.box,-release.number"
    assert api.post(path, {"name": "x", "sort": "box,colour"}).status_code == 400


def test_public_sort_ignores_private_fields(
    anon_api: Any, library: Library, stocked: dict[str, Item]
) -> None:
    library.public_token = "tok"
    library.save()
    stocked["zelda"].current_value = Decimal(99)
    stocked["zelda"].save()
    response = anon_api.get("/public/libraries/tok/items", {"sort": "-copy.value"})
    # The value isn't public: sorted by title only.
    assert next(i["title"] for i in response.json()["items"]) == "Mario Kart 8 Deluxe"
