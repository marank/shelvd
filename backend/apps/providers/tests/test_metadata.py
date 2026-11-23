import datetime
from collections.abc import Callable
from typing import Any

import pytest
from django.core.cache import cache
from django.core.files.base import ContentFile

from apps.catalog.models import Company, Genre, Platform, Release, Work
from apps.providers.services.integrations import save

from .conftest import PNG
from .fakes import router


@pytest.fixture
def mario(make_release: Callable[..., Release], switch: Platform) -> Release:
    return make_release("Mario Odyssey", switch)


def test_candidates_one_per_game(api: Any, igdb: list[str], mario: Release) -> None:
    url = f"/catalog/works/{mario.work_id}/metadata/igdb/candidates"
    found = api.get(url).json()
    assert 'search "Mario Odyssey"' in igdb[-1]
    assert found == [
        {
            "external_id": "26758",
            "title": "Super Mario Odyssey",
            "year": 2017,
            "platforms": ["Nintendo Switch", "Toaster"],
            "summary": "Cappy!",
            "cover_url": "https://images.igdb.com/igdb/image/upload/t_cover_big_2x/co1mxf.jpg",
        }
    ]
    api.get(url, {"q": " Odyssey "})
    assert 'search "Odyssey"' in igdb[-1]


def ids(changes: list[dict[str, Any]]) -> dict[str, tuple[str, bool]]:
    """{field (release fields prefixed by platform slug): (kind, suggested)}"""
    out = {}
    for c in changes:
        prefix = (
            ""
            if c["release_id"] is None
            else Release.objects.get(pk=c["release_id"]).platform.slug + "."
        )
        out[prefix + c["field"]] = (c["kind"], c["suggested"])
    return out


def test_preview_and_apply_empty_game(
    api: Any, igdb: list[str], make_release: Callable[..., Release], switch: Platform, nds: Platform
) -> None:
    empty = make_release("Mario Odyssey", switch)
    other_platform = Release.objects.create(work=empty.work, platform=nds)
    url = f"/catalog/works/{empty.work_id}/metadata/igdb"

    preview = api.get(f"{url}/26758").json()
    assert preview["title"] == "Super Mario Odyssey"
    assert ids(preview["changes"]) == {
        # Another title is only offered.
        "title": ("differs", False),
        "summary": ("fill", True),
        "first_release_date": ("fill", True),
        "genres": ("fill", True),
        "developers": ("fill", True),
        # Only the Switch: IGDB doesn't list the game on the DS.
        "switch.release_date": ("fill", True),
        "switch.publisher": ("fill", True),
        "cover": ("fill", True),
    }
    date_change = next(c for c in preview["changes"] if c["field"] == "release_date")
    assert date_change["current"] == {"text": "", "date": None, "precision": "day", "image": None}
    assert date_change["proposed"]["date"] == "2017-10-27"
    assert Work.objects.get(pk=empty.work_id).external_ids == {}  # a preview changes nothing

    chosen = [c["id"] for c in preview["changes"] if c["field"] not in ("genres", "title")]
    chosen.append("bogus")
    applied = api.post(url, {"external_id": "26758", "changes": chosen}).json()["applied"]
    assert sorted(applied) == sorted(chosen[:-1])
    work = Work.objects.get(pk=empty.work_id)
    assert work.title == "Mario Odyssey"  # not chosen
    assert work.external_ids == {"igdb": "26758"}
    assert work.summary == "Cappy!"
    assert not work.genres.exists()  # not chosen
    release = Release.objects.get(pk=empty.pk)
    assert release.release_date == datetime.date(2017, 10, 27)
    assert release.publisher
    assert release.publisher.name == "Nintendo"
    assert work.cover
    assert not release.cover
    other_platform.refresh_from_db()
    assert other_platform.publisher is None
    assert not other_platform.cover

    # Only title and genres are left; the work has a cover now.
    assert ids(api.get(f"{url}/26758").json()["changes"]) == {
        "title": ("differs", False),
        "genres": ("fill", True),
    }
    assert api.get(f"/catalog/works/{empty.work_id}").json()["external_ids"] == {"igdb": "26758"}


def test_precise_dates_suggested_differences_not(
    api: Any, igdb: list[str], make_release: Callable[..., Release], switch: Platform
) -> None:
    release = make_release(
        "Mario", switch, year=2020, publisher="Own", genres=("Jump",), developers=("Nintendo EPD",)
    )
    work = release.work
    work.summary = "Mine"
    work.save()
    release.release_precision = "half"
    release.release_date = datetime.date(2017, 7, 1)
    release.cover.save("own.png", ContentFile(PNG))
    url = f"/catalog/works/{work.pk}/metadata/igdb"

    changes = api.get(f"{url}/26758").json()["changes"]
    assert ids(changes) == {
        "title": ("differs", False),
        "summary": ("differs", False),
        "first_release_date": ("differs", False),
        "genres": ("differs", False),
        # developers are the same
        "switch.release_date": ("precise", True),
        "switch.publisher": ("differs", False),
        "cover": ("fill", True),
    }

    picked = [c["id"] for c in changes if c["suggested"] or c["field"] == "summary"]
    api.post(url, {"external_id": "26758", "changes": picked})
    work.refresh_from_db()
    release.refresh_from_db()
    assert work.summary == "Cappy!"
    assert work.first_release_date == datetime.date(2020, 1, 1)
    assert list(work.genres.values_list("name", flat=True)) == ["Jump"]
    assert release.release_precision == "day"
    assert release.release_date == datetime.date(2017, 10, 27)
    assert release.publisher == Company.objects.get(name="Own")
    assert release.cover_source == ""
    assert not Genre.objects.filter(name="Jump 'n' Run").exists()


def test_dates_not_worse_and_same_precision_differs(
    api: Any, igdb: list[str], make_release: Callable[..., Release], switch: Platform
) -> None:
    release = make_release("Mario", switch)
    release.release_date = datetime.date(2017, 10, 26)
    release.save()
    url = f"/catalog/works/{release.work_id}/metadata/igdb/26758"
    assert ids(api.get(url).json()["changes"])["switch.release_date"] == ("differs", False)
    release.release_date = datetime.date(2017, 10, 27)
    release.save()
    assert "switch.release_date" not in ids(api.get(url).json()["changes"])
    # A finer date outside our period contradicts it rather than making it exact.
    release.release_precision, release.release_date = "month", datetime.date(2018, 3, 1)
    release.save()
    assert ids(api.get(url).json()["changes"])["switch.release_date"] == ("differs", False)


def test_errors(api: Any, mario: Release, monkeypatch: pytest.MonkeyPatch) -> None:
    url = f"/catalog/works/{mario.work_id}/metadata/igdb"
    # Switched off.
    assert api.get(f"{url}/candidates").status_code == 400
    assert api.post(url, {"external_id": "1", "changes": []}).status_code == 400
    assert api.get(f"/catalog/works/{mario.work_id}/metadata/nope/candidates").status_code == 400

    save("igdb", enabled=True, secrets={"client_id": "id", "client_secret": "secret"})
    cache.clear()
    monkeypatch.setattr("httpx.post", router({}))  # unreachable
    assert api.get(f"{url}/candidates").status_code == 502
    assert api.post(url, {"external_id": "1", "changes": []}).status_code == 502


def test_unknown_game(api: Any, igdb: list[str], mario: Release) -> None:
    url = f"/catalog/works/{mario.work_id}/metadata/igdb"
    assert api.get(f"{url}/1").status_code == 404
    assert api.post(url, {"external_id": "1", "changes": []}).status_code == 404
    assert Work.objects.get(pk=mario.work_id).external_ids == {}
