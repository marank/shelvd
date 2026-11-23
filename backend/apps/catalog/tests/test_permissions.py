"""Only admins change the catalog; library editors may add games and barcodes, which wait
for review; their creator may still fix them until then."""

from collections.abc import Callable
from typing import Any

import pytest

from apps.accounts.models import User
from apps.catalog.models import Barcode, Company, Genre, Platform, Release, ReviewStatus, Work
from apps.collection.models import Library, LibraryMember, Role


@pytest.fixture
def editor(other: User, user: User) -> User:
    """bob: no admin, but editor of alice's library."""
    library = Library.objects.create(name="Shared", owner=user)
    LibraryMember.objects.create(library=library, user=other, role=Role.EDITOR)
    return other


@pytest.fixture
def mario(make_release: Callable[..., Release], switch: Platform) -> Release:
    return make_release("Super Mario Odyssey", switch)


def test_plain_users_cannot_change_the_catalog(
    other_api: Any, mario: Release, make_release: Callable[..., Release], switch: Platform
) -> None:
    genre = Genre.objects.create(name="Jump")
    company = Company.objects.create(name="Nintendo")
    other = make_release("Zelda", switch)
    w, r = mario.work_id, mario.pk
    forbidden = [
        ("patch", f"/catalog/works/{w}", {"title": "X"}),
        ("patch", f"/catalog/releases/{r}", {"edition": "X"}),
        ("post", f"/catalog/works/{w}/merge", {"target_id": str(other.work_id)}),
        ("post", f"/catalog/releases/{r}/move", {"title": "X"}),
        ("delete", f"/catalog/works/{w}/cover", None),
        ("patch", f"/catalog/genres/{genre.pk}", {"name": "X"}),
        ("delete", f"/catalog/genres/{genre.pk}", None),
        ("post", f"/catalog/genres/{genre.pk}/merge", {"target_id": str(genre.pk)}),
        ("patch", f"/catalog/platforms/{switch.pk}", {"name": "X"}),
        ("delete", f"/catalog/platforms/{switch.pk}", None),
        ("post", "/catalog/platforms", {"name": "X"}),
        ("delete", f"/catalog/platforms/{switch.pk}/icon", None),
        ("put", f"/catalog/works/{w}/facts/hltb", {"external_id": "1"}),
        ("delete", f"/catalog/works/{w}/facts/hltb", None),
        ("get", f"/catalog/works/{w}/facts/hltb/candidates", None),
        ("post", f"/catalog/works/{w}/facts/refresh?force=true", None),
        ("post", f"/catalog/releases/{r}/cover-from", {"token": "x"}),
        ("get", f"/catalog/works/{w}/metadata/igdb/candidates", None),
        ("post", f"/catalog/works/{w}/metadata/igdb", {"external_id": "1", "changes": []}),
        ("get", f"/catalog/companies/{company.pk}/description/wikipedia/candidates", None),
        ("get", "/catalog/review", None),
        ("get", "/catalog/review/count", None),
        ("post", "/catalog/review/approve", {}),
        # Not an editor anywhere: may not add games either.
        ("post", "/catalog/releases", {"title": "X", "platform_id": str(switch.pk)}),
        ("post", f"/catalog/releases/{r}/barcodes", {"code": "4006381333931"}),
        ("get", f"/catalog/releases/{r}/cover-candidates", None),
        ("post", "/lookup/import", {"provider": "igdb", "external_id": "1",
                                    "platform_id": str(switch.pk), "region": "pal"}),
    ]  # fmt: skip
    for method, path, body in forbidden:
        call = getattr(other_api, method)
        response = call(path) if body is None and method in ("get", "delete") else call(path, body)
        assert response.status_code == 403, (method, path, response.status_code)
    # Refreshing what's outdated is fine for everyone.
    assert other_api.post(f"/catalog/works/{w}/facts/refresh").status_code == 200
    work = other_api.get(f"/catalog/works/{w}").json()
    assert work["can_edit"] is False
    assert work["review_status"] == "approved"
    assert other_api.get("/auth/me").json()["can_contribute"] is False


def test_editors_add_unreviewed_entries_and_admins_approve_them(
    editor: User, other_api: Any, api: Any, mario: Release, switch: Platform
) -> None:
    assert other_api.get("/auth/me").json()["can_contribute"] is True
    created = other_api.post(
        "/catalog/releases",
        {"title": "Homebrew", "platform_id": str(switch.pk), "barcode": "4006381333931"},
    ).json()
    assert created["review_status"] == "pending"
    assert created["can_edit"] is True
    assert created["pending_barcodes"] == ["4006381333931"]
    release = Release.objects.get(pk=created["id"])
    assert release.created_by == editor
    assert release.work.pending

    # The creator may fix typos while it waits; others (but admins) may not.
    fixed = other_api.patch(f"/catalog/releases/{release.pk}", {"edition": "Deluxe"})
    assert fixed.status_code == 200
    renamed = other_api.patch(f"/catalog/works/{release.work_id}", {"title": "Homebrew!"})
    assert renamed.status_code == 200
    # A barcode for a reviewed release is unreviewed too.
    assigned = other_api.post(f"/catalog/releases/{mario.pk}/barcodes", {"code": "96385074"})
    assert assigned.json()["pending_barcodes"] == ["96385074"]
    # Pending barcodes answer scans right away.
    assert [r["id"] for r in other_api.get("/lookup/barcode/96385074").json()["known"]] == [
        str(mario.pk)
    ]

    queue = api.get("/catalog/review").json()
    assert queue["count"] == 3
    assert [(e["kind"], e["created_by"]) for e in queue["entries"]] == [
        ("release", "bob"),
        ("barcode", "bob"),
        ("barcode", "bob"),
    ]
    assert api.get("/catalog/review/count").json() == {"count": 4}  # + the game itself
    wrong = Barcode.objects.get(code="96385074")
    assert api.delete(f"/catalog/barcodes/{wrong.pk}").status_code == 204
    right = Barcode.objects.get(code="4006381333931")
    approved = api.post(
        "/catalog/review/approve", {"releases": [str(release.pk)], "barcodes": [str(right.pk)]}
    ).json()
    assert approved == {"approved": 3}  # release, its game, the barcode
    release.refresh_from_db()
    assert release.review_status == ReviewStatus.APPROVED
    assert release.reviewed_by is not None
    assert Work.objects.get(pk=release.work_id).review_status == ReviewStatus.APPROVED
    assert api.get("/catalog/review").json() == {"count": 0, "entries": []}
    # Reviewed: the creator can't change it any more.
    assert other_api.patch(f"/catalog/releases/{release.pk}", {"edition": "X"}).status_code == 403


def test_admins_entries_are_reviewed_and_work_alone_shows_up(
    api: Any, user: User, switch: Platform
) -> None:
    created = api.post("/catalog/releases", {"title": "Mine", "platform_id": str(switch.pk)})
    assert created.json()["review_status"] == "approved"
    work = Work.objects.create(title="Lonely", review_status=ReviewStatus.PENDING)
    entries = api.get("/catalog/review").json()["entries"]
    assert [(e["kind"], e["title"], e["created_by"]) for e in entries] == [("work", "Lonely", None)]
    assert api.post("/catalog/review/approve", {"works": [str(work.pk)]}).json() == {"approved": 1}
