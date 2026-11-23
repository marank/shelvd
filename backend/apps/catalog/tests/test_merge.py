# ruff: noqa: E501  (title tables read better unwrapped)
import io
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from django.core.files.base import ContentFile
from django.core.management import call_command

from apps.catalog.models import Genre, Platform, Release, Work
from apps.catalog.services.editions import split_edition
from apps.catalog.services.merge import merge_works, move_release
from apps.catalog.services.releases import remove_work_cover
from apps.catalog.signals import work_merged
from apps.collection.models import Item, Library


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Dave The Diver: Complete Edition", ("Dave The Diver", "Complete Edition")),
        ("The Witcher 3 - Wild Hunt Complete Edition", ("The Witcher 3 - Wild Hunt", "Complete Edition")),
        ("Stardew Valley - Collector's Edition", ("Stardew Valley", "Collector's Edition")),
        ("Rayman: 30th Anniversary Edition", ("Rayman", "30th Anniversary Edition")),
        ("Kirby (Nintendo Switch 2 Edition)", ("Kirby", "Nintendo Switch 2 Edition")),
        ("Death Stranding Director's Cut", ("Death Stranding", "Director's Cut")),
        ("Deluxe Edition", ("Deluxe Edition", "")),
        ("Zelda", ("Zelda", "")),
    ],
)  # fmt: skip
def test_split_edition(title: str, expected: tuple[str, str]) -> None:
    assert split_edition(title) == expected


def test_move_and_merge(
    api: Any,
    library: Library,
    make_release: Callable[..., Release],
    switch: Platform,
    nds: Platform,
) -> None:
    base = make_release("Dave the Diver", switch, genres=("Adventure",))
    complete = make_release("Dave The Diver: Complete Edition", switch)
    complete.work.summary = "Diving and sushi."
    complete.work.save()
    Item.objects.create(library=library, release=complete)

    merged = api.post(f"/catalog/works/{complete.work_id}/merge", {"target_id": str(base.work_id)})
    assert merged.status_code == 200, merged.json()
    body = merged.json()
    assert body["title"] == "Dave the Diver"
    assert body["summary"] == "Diving and sushi."  # filled from the merged game
    assert len(body["releases"]) == 2
    complete.refresh_from_db()
    assert (complete.work_id, complete.edition, complete.title) == (
        base.work_id,
        "Complete Edition",
        "",
    )
    assert Item.objects.get().release == complete  # copies came along
    assert not Work.objects.filter(title__startswith="Dave The Diver:").exists()
    assert (
        api.post(
            f"/catalog/works/{base.work_id}/merge", {"target_id": str(base.work_id)}
        ).status_code
        == 400
    )

    # Split it out again: the release becomes a game of its own.
    own = api.post(
        f"/catalog/releases/{complete.pk}/move", {"title": "Dave the Diver Complete"}
    ).json()
    assert own["work_title"] == "Dave the Diver Complete"
    assert own["work_id"] != str(base.work_id)
    new_work = Work.objects.get(pk=own["work_id"])
    assert [g.name for g in new_work.genres.all()] == ["Adventure"]
    # And back: moving the only release away deletes the then empty game.
    back = api.post(f"/catalog/releases/{complete.pk}/move", {"work_id": str(base.work_id)}).json()
    assert back["work_id"] == str(base.work_id)
    assert not Work.objects.filter(pk=new_work.pk).exists()
    assert (
        api.post(
            f"/catalog/releases/{complete.pk}/move", {"work_id": str(base.work_id)}
        ).status_code
        == 400
    )

    # A release with a different regional title keeps it.
    jp = make_release("Pocket Monsters", nds)
    moved = api.post(f"/catalog/releases/{jp.pk}/move", {"work_id": str(base.work_id)}).json()
    assert moved["title"] == "Pocket Monsters"
    assert api.post(f"/catalog/releases/{jp.pk}/move", {}).json()["work_title"] == "Pocket Monsters"


def test_work_search(api: Any, make_release: Callable[..., Release], switch: Platform) -> None:
    one = make_release("Hyrule Warriors", switch)
    make_release("Hyrule Warriors: Age of Calamity", switch)
    found = api.get("/catalog/works", {"q": "hyrule warriors"}).json()
    assert [w["title"] for w in found] == ["Hyrule Warriors", "Hyrule Warriors: Age of Calamity"]
    assert found[0]["platforms"] == ["Switch"]
    assert found[0]["releases"] == 1
    assert found[0]["cover_url"] is None
    excluded = api.get("/catalog/works", {"q": "hyrule", "exclude": str(one.work_id)}).json()
    assert [w["title"] for w in excluded] == ["Hyrule Warriors: Age of Calamity"]


def test_split_editions_command(make_release: Callable[..., Release], switch: Platform) -> None:
    make_release("Cyberpunk 2077", switch)
    ultimate = make_release("Cyberpunk 2077: Ultimate Edition", switch)
    witcher = make_release("The Witcher 3 - Wild Hunt Complete Edition", switch)
    Genre.objects.create(name="RPG")
    out = io.StringIO()
    call_command("split_editions", "--dry-run", stdout=out)
    assert "1 merged, 1 renamed," in out.getvalue()
    assert Work.objects.count() == 3
    call_command("split_editions", stdout=io.StringIO())
    ultimate.refresh_from_db()
    witcher.refresh_from_db()
    assert ultimate.work.title == "Cyberpunk 2077"
    assert ultimate.edition == "Ultimate Edition"
    assert (witcher.work.title, witcher.edition) == (
        "The Witcher 3 - Wild Hunt",
        "Complete Edition",
    )
    assert witcher.title == ""
    assert Work.objects.count() == 2


def test_split_editions_cleans_release_titles(
    make_release: Callable[..., Release], switch: Platform
) -> None:
    # Already merged earlier: the edition is set, but the title still repeats it.
    dave = make_release("Dave the Diver", switch)
    dave.title, dave.edition = "Dave The Diver: Complete Edition", "Complete Edition"
    dave.save()
    remake = make_release("Rayman", switch)
    remake.title, remake.edition = "Rayman Origins: Gold Edition", "Complete Edition"
    remake.save()
    out = io.StringIO()
    call_command("split_editions", stdout=out)
    assert "1 release titles cleaned." in out.getvalue()
    dave.refresh_from_db()
    remake.refresh_from_db()
    assert (dave.title, dave.edition) == ("", "Complete Edition")
    # A different edition in the title is the release's own business: keep it.
    assert remake.title == "Rayman Origins: Gold Edition"


def test_move_keeps_the_cover_of_a_game_that_stays(
    make_release: Callable[..., Release], switch: Platform, nds: Platform
) -> None:
    """A game keeping other releases keeps its cover file to itself: removing the target's
    cover later must not delete it."""
    moved = make_release("Pokémon Black", switch)
    Release.objects.create(work=moved.work, platform=nds, region="na")
    source = moved.work
    source.cover.save("key.png", ContentFile(b"png"), save=True)
    target = make_release("Pokemon Black", nds).work

    move_release(moved, target)
    remove_work_cover(target)
    source.refresh_from_db()
    assert Path(source.cover.path).exists()


@pytest.mark.django_db
def test_merge_tells_others_to_move_their_rows() -> None:
    """Add-ons keep rows pointing at games; they move with the merge (catalog.signals)."""
    seen: list[tuple[str, str]] = []

    def receiver(sender: object, source: Work, target: Work, **kwargs: object) -> None:
        seen.append((source.title, target.title))

    work_merged.connect(receiver)
    try:
        source = Work.objects.create(title="Old")
        target = Work.objects.create(title="New")
        merge_works(source, target)
    finally:
        work_merged.disconnect(receiver)
    assert seen == [("Old", "New")]
