from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from ninja.errors import HttpError

from apps.collection.models import Item, Library, Location
from apps.collection.selectors.conditions import KNOWN, parse_condition, parse_conditions


def titles(api: Any, library: Library, *where: str, match: str = "all") -> list[str]:
    response = api.get(f"/libraries/{library.pk}/items", {"where": list(where), "match": match})
    assert response.status_code == 200, response.json()
    return [item["title"] for item in response.json()["items"]]


@pytest.fixture
def boxed(library: Library, stocked: dict[str, Item]) -> dict[str, Item]:
    room = Location.objects.create(library=library, name="Home", kind="room")
    box = Location.objects.create(library=library, name="Box A", kind="box", parent=room)
    stocked["mk8"].location = box
    stocked["mk8"].current_value = Decimal(45)
    stocked["mk8"].acquired_on = date(2024, 3, 1)
    stocked["mk8"].save()
    stocked["zelda"].location = room
    stocked["zelda"].current_value = Decimal(80)
    stocked["zelda"].save()
    return stocked


def test_patterns(api: Any, library: Library, boxed: dict[str, Item]) -> None:
    assert titles(api, library, "game.title~M*") == ["Mario Kart 8 Deluxe"]
    assert titles(api, library, "game.title~*zelda*") == ["Zelda: Breath of the Wild"]
    # Without wildcards: contains.
    assert titles(api, library, "game.title~rush") == ["Sonic Rush"]
    assert titles(api, library, "game.title!~*o*") == []
    assert titles(api, library, "game.title~?onic*") == ["Sonic Rush"]
    assert titles(api, library, "copy.notes~signed") == ["Zelda: Breath of the Wild"]


def test_presence_and_keys(api: Any, library: Library, boxed: dict[str, Item]) -> None:
    # "In a box", wherever the box is; and copies not in any box.
    assert titles(api, library, "location.box?") == ["Mario Kart 8 Deluxe"]
    assert titles(api, library, "location.box!?") == ["Sonic Rush", "Zelda: Breath of the Wild"]
    assert titles(api, library, "location.room~Home") == [
        "Mario Kart 8 Deluxe",
        "Zelda: Breath of the Wild",
    ]
    nds = boxed["sonic"].release.platform_id
    assert titles(api, library, f"platform.name={nds}") == ["Sonic Rush"]
    assert titles(api, library, f"platform.name!={nds}") == [
        "Mario Kart 8 Deluxe",
        "Zelda: Breath of the Wild",
    ]
    assert titles(api, library, "game.genres~rpg") == ["Zelda: Breath of the Wild"]


def test_ranges(api: Any, library: Library, boxed: dict[str, Item]) -> None:
    assert titles(api, library, "release.year<=2010") == ["Sonic Rush"]
    assert titles(api, library, "copy.value>=50") == ["Zelda: Breath of the Wild"]
    assert titles(api, library, "copy.value><40..50") == ["Mario Kart 8 Deluxe"]
    assert titles(api, library, "copy.acquired>=2024-01-01") == ["Mario Kart 8 Deluxe"]
    assert titles(api, library, "copy.value?") == [
        "Mario Kart 8 Deluxe",
        "Zelda: Breath of the Wild",
    ]


def test_all_or_any(api: Any, library: Library, boxed: dict[str, Item]) -> None:
    assert titles(api, library, "game.title~sonic*", "location.box?") == []
    assert titles(api, library, "game.title~sonic*", "location.box?", match="any") == [
        "Mario Kart 8 Deluxe",
        "Sonic Rush",
    ]
    tree = api.get(
        f"/libraries/{library.pk}/tree", {"group_by": "location.box", "where": "location.box?"}
    ).json()
    assert tree["total"] == 1


@pytest.mark.parametrize(
    "text",
    [
        "", "title", "game.title?x", "colour.x~a", "game.title=x", "location.box~",
        "release.year>=soon", "release.year><2000", "copy.acquired>=2024-13-01",
        "platform.name=",
    ],
)  # fmt: skip
def test_invalid(text: str) -> None:
    with pytest.raises(HttpError):
        parse_condition(text)


def test_every_field_and_operator(api: Any, library: Library, boxed: dict[str, Item]) -> None:
    for field in KNOWN:
        assert (
            len(titles(api, library, f"{field}?")) + len(titles(api, library, f"{field}!?")) == 3
        ), field
    # Public pages drop conditions on private fields.
    assert (
        parse_conditions(["location.box?", "game.title~a"], allowed={"game.title"})[0].field
        == "game.title"
    )
    assert api.get(f"/libraries/{library.pk}/items", {"where": "nope"}).status_code == 400


def test_subfields(api: Any, library: Library, boxed: dict[str, Item]) -> None:
    from apps.collection.models import Loan, Person

    # "Place › kind is box": copies lying directly in a box.
    assert titles(api, library, "location.kind=box") == ["Mario Kart 8 Deluxe"]
    assert titles(api, library, "location.kind=room|shelf") == ["Zelda: Breath of the Wild"]
    assert titles(api, library, "location.name~home") == ["Zelda: Breath of the Wild"]
    max_ = Person.objects.create(library=library, name="Max")
    Loan.objects.create(
        item=boxed["sonic"], borrower=max_, lent_on=date(2026, 1, 1), due_on=date(2000, 1, 1)
    )
    assert titles(api, library, "loan.overdue=yes") == ["Sonic Rush"]
    assert titles(api, library, "loan.due<=2001-01-01") == ["Sonic Rush"]
    assert titles(api, library, "loan.since?") == ["Sonic Rush"]
    kinds = api.get(f"/libraries/{library.pk}/tree", {"group_by": "location.kind"}).json()
    assert [n["key"] for n in kinds["nodes"]] == ["room", "box", "none"]


def test_added_is_a_local_date(api: Any, library: Library, stocked: dict[str, Item]) -> None:
    """Like grouping: added at 00:30 in Berlin on the 1st is the 1st, not the UTC 31st."""
    added = datetime(2025, 11, 1, 0, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    Item.objects.filter(pk=stocked["mk8"].pk).update(created_at=added)
    assert titles(api, library, "copy.added<=2025-10-31") == []
    assert titles(api, library, "copy.added<=2025-11-01") == ["Mario Kart 8 Deluxe"]


def test_how_its_played(api: Any, library: Library, stocked: dict[str, Item]) -> None:
    work = stocked["mk8"].release.work
    work.game_modes = ["Single player", "Multiplayer"]
    work.perspectives = ["Third person"]
    work.languages = {"German": ["audio", "interface"]}
    work.save()
    release = stocked["mk8"].release
    release.players_offline, release.players_online = 4, 12
    release.save()
    assert titles(api, library, "game.modes=Multiplayer") == ["Mario Kart 8 Deluxe"]
    assert titles(api, library, "game.perspectives~third*") == ["Mario Kart 8 Deluxe"]
    assert titles(api, library, "game.languages=German") == ["Mario Kart 8 Deluxe"]
    assert titles(api, library, "release.players_offline>=2") == ["Mario Kart 8 Deluxe"]
    assert titles(api, library, "release.players_online!?") == [
        "Sonic Rush",
        "Zelda: Breath of the Wild",
    ]
    tree = api.get(f"/libraries/{library.pk}/tree", {"group_by": "release.players_offline"}).json()
    assert [node["label"] for node in tree["nodes"]][:1] == ["4"]
