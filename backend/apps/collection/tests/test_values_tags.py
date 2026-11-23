from decimal import Decimal
from typing import Any

from apps.catalog.models import Series
from apps.collection.models import Item, Library


def test_tags_values_and_new_groupings(
    api: Any, library: Library, stocked: dict[str, Item]
) -> None:
    path = f"/libraries/{library.pk}/items"
    zelda = stocked["zelda"]
    patched = api.patch(
        f"{path}/{zelda.pk}", {"current_value": "120.50", "tags": ["Steelbook", " signed ", ""]}
    ).json()
    assert patched["tags"] == ["Steelbook", "signed"]
    assert patched["current_value"] == "120.50"
    api.patch(f"{path}/{stocked['mk8'].pk}", {"current_value": "30"})
    created = api.post(
        path, {"release_id": str(stocked["sonic"].release_id), "tags": ["Steelbook"]}
    ).json()
    assert created["tags"] == ["Steelbook"]
    assert api.patch(f"{path}/{zelda.pk}", {"notes": "x"}).json()["tags"] == ["Steelbook", "signed"]

    release = zelda.release
    release.age_rating = "USK 12"
    release.save()
    release.work.series.set([Series.objects.create(name="The Legend of Zelda")])

    tree = api.get(f"/libraries/{library.pk}/tree", {"group_by": "platform.name"}).json()
    assert Decimal(tree["total_value"]) == Decimal("150.50")
    switch = next(n for n in tree["nodes"] if n["label"] == "Nintendo Switch")
    assert Decimal(switch["value"]) == Decimal("150.50")
    tags = api.get(f"/libraries/{library.pk}/tree", {"group_by": "copy.tags"}).json()["nodes"]
    assert [(n["label"], n["count"]) for n in tags] == [("signed", 1), ("Steelbook", 2), ("", 2)]
    series = api.get(
        f"/libraries/{library.pk}/tree", {"group_by": ["game.series", "release.age_rating"]}
    ).json()
    zelda_node = next(n for n in series["nodes"] if n["label"] == "The Legend of Zelda")
    assert zelda_node["children"][0]["label"] == "USK 12"
    media = api.get(f"/libraries/{library.pk}/tree", {"group_by": "game.kind"}).json()["nodes"]
    assert [n["key"] for n in media] == ["game"]

    assert api.get(path, {"q": "steelbook"}).json()["count"] == 2
    by_value = api.get(path, {"sort": "-copy.value"}).json()["items"]
    assert by_value[0]["id"] == str(zelda.pk)
    assert api.get(path, {"q": "zelda usk"}).json()["count"] == 1

    library.public_token = "tok"
    library.save()
    public = api.get(
        "/public/libraries/tok/tree", {"group_by": ["platform.name", "game.series"]}
    ).json()
    assert public["total_value"] == "0"
    assert all(n["value"] == "0" for n in public["nodes"])
    assert all(c["value"] == "0" for n in public["nodes"] for c in n["children"])


def test_title_sort_ignores_articles(
    api: Any, library: Library, make_release: Any, switch: Any
) -> None:
    for title in ("The Witcher 3", "Astral Chain", "Die Siedler", "Zelda"):
        Item.objects.create(library=library, release=make_release(title, switch))
    items = api.get(f"/libraries/{library.pk}/items").json()["items"]
    assert [i["title"] for i in items] == ["Astral Chain", "Die Siedler", "The Witcher 3", "Zelda"]
    letters = api.get(f"/libraries/{library.pk}/tree", {"group_by": "game.letter"}).json()["nodes"]
    assert [n["label"] for n in letters] == ["A", "S", "W", "Z"]


def test_release_and_work_fields(api: Any, make_release: Any, switch: Any) -> None:
    release = make_release("Hades", switch)
    body = api.patch(
        f"/catalog/releases/{release.pk}",
        {"age_rating": "PEGI 12", "product_code": "LA-H-AXVXA-EUR", "release_number": 7},
    ).json()
    assert (body["age_rating"], body["product_code"], body["release_number"]) == (
        "PEGI 12",
        "LA-H-AXVXA-EUR",
        7,
    )
    assert (
        api.patch(f"/catalog/releases/{release.pk}", {"release_number": None}).json()[
            "release_number"
        ]
        is None
    )
    # A typed name is cleaned; picking the same name again (any case) finds it.
    work = api.patch(f"/catalog/works/{release.work_id}", {"series": [{"name": " Hades "}]}).json()
    assert [s["name"] for s in work["series"]] == ["Hades"]
    again = api.patch(f"/catalog/works/{release.work_id}", {"series": [{"name": "hades"}]})
    assert again.json()["series"] == work["series"]
    assert Series.objects.filter(name__iexact="hades").count() == 1
    created = api.post(
        "/catalog/releases",
        {
            "title": "Celeste",
            "platform_id": str(switch.pk),
            "series": [{"name": "Celeste"}],
            "age_rating": "USK 6",
        },
    ).json()
    assert ([s["name"] for s in created["series"]], created["age_rating"]) == (["Celeste"], "USK 6")
