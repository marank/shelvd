"""Franchises are terms like series: a page, renaming, merging, a field to group by."""

from collections.abc import Callable
from typing import Any

from apps.catalog.models import Franchise, Platform, Release, Series
from apps.collection.models import Item, Library


def test_franchises_as_terms(
    api: Any, library: Library, make_release: Callable[..., Release], switch: Platform
) -> None:
    kart = make_release("Mario Kart 8", switch)
    odyssey = make_release("Super Mario Odyssey", switch)
    mario = Franchise.objects.create(name="Mario")
    copy = Franchise.objects.create(name="mario bros")
    kart.work.franchises.add(mario)
    odyssey.work.franchises.add(copy)
    odyssey.work.series.add(Series.objects.create(name="Super Mario"))
    Item.objects.create(library=library, release=kart)
    Item.objects.create(library=library, release=odyssey)

    assert [t["name"] for t in api.get("/catalog/franchises").json()] == ["Mario", "mario bros"]
    detail = api.get(f"/catalog/franchises/{copy.pk}").json()
    assert [w["title"] for w in detail["works"]] == ["Super Mario Odyssey"]
    assert {r["kind"] for r in detail["related"]} == {"series"}
    # The game shows them, with ids for the edit form's picker.
    work = api.get(f"/catalog/works/{odyssey.work_id}").json()
    assert [f["name"] for f in work["franchises"]] == ["mario bros"]
    patched = api.patch(f"/catalog/works/{odyssey.work_id}", {"franchises": [{"name": "Nintendo"}]})
    assert [f["name"] for f in patched.json()["franchises"]] == ["Nintendo"]
    api.patch(f"/catalog/works/{odyssey.work_id}", {"franchises": [{"id": str(copy.pk)}]})

    merged = api.post(f"/catalog/franchises/{copy.pk}/merge", {"target_id": str(mario.pk)})
    assert merged.status_code == 200
    assert not Franchise.objects.filter(pk=copy.pk).exists()
    assert odyssey.work.franchises.get() == mario

    tree = api.get(f"/libraries/{library.pk}/tree", {"group_by": "game.franchises"}).json()
    assert [(n["label"], n["count"]) for n in tree["nodes"]] == [("Mario", 2)]
    found = api.get(f"/libraries/{library.pk}/items", {"q": "mario"}).json()
    assert found["count"] == 2
    release = api.get(f"/catalog/releases/{kart.pk}").json()
    assert [f["name"] for f in release["franchises"]] == ["Mario"]
