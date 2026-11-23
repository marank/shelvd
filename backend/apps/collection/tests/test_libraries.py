import datetime
from collections.abc import Callable
from typing import Any

from apps.accounts.models import User
from apps.catalog.models import Platform, Release
from apps.collection.models import Item, Library, LibraryMember, Loan, Overview, Person


def test_create_and_list(api: Any, user: User) -> None:
    created = api.post("/libraries", {"name": " Spiele ", "description": "alles"})
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Spiele"
    assert body["role"] == "owner"
    assert body["item_count"] == 0
    # Every new library starts with one overview for its owner.
    assert Overview.objects.get(library_id=body["id"]).group_by == ["platform.name"]
    assert [lib["name"] for lib in api.get("/libraries").json()] == ["Spiele"]
    assert api.post("/libraries", {"name": " "}).status_code == 400


def test_update_delete_public_link(api: Any, library: Library) -> None:
    path = f"/libraries/{library.pk}"
    assert api.patch(path, {"name": "Konsolen", "description": None}).json()["name"] == "Konsolen"
    linked = api.post(f"{path}/public-link").json()
    assert linked["public_token"]
    # Enabling twice keeps the same link.
    assert api.post(f"{path}/public-link").json()["public_token"] == linked["public_token"]
    assert api.delete(f"{path}/public-link").json()["public_token"] is None
    assert api.get(path).json()["name"] == "Konsolen"
    assert api.delete(path).status_code == 204
    assert not Library.objects.exists()


def test_members_and_roles(
    api: Any, other_api: Any, library: Library, other: User, stocked: dict[str, Item]
) -> None:
    path = f"/libraries/{library.pk}"
    # Invisible to others: 404, not 403.
    assert other_api.get(path).status_code == 404
    assert api.post(f"{path}/members", {"username": "nobody"}).status_code == 404
    assert api.post(f"{path}/members", {"username": "alice"}).status_code == 400
    member = api.post(f"{path}/members", {"username": "BOB"})
    assert member.status_code == 201
    assert member.json() == {"id": member.json()["id"], "username": "bob", "role": "viewer"}
    assert api.post(f"{path}/members", {"username": "bob"}).status_code == 409
    assert [m["username"] for m in api.get(f"{path}/members").json()] == ["bob"]

    # Viewer: reads, may not write or manage.
    seen = other_api.get(path).json()
    assert seen["role"] == "viewer"
    assert seen["public_token"] is None
    assert seen["item_count"] == 3
    assert other_api.get(f"{path}/items").json()["count"] == 3
    release_id = str(stocked["mk8"].release_id)
    assert other_api.post(f"{path}/items", {"release_id": release_id}).status_code == 403
    assert other_api.patch(path, {"name": "mine"}).status_code == 403
    assert other_api.post(f"{path}/public-link").status_code == 403

    member_id = member.json()["id"]
    assert api.patch(f"{path}/members/{member_id}", {"role": "editor"}).json()["role"] == "editor"
    assert other_api.post(f"{path}/items", {"release_id": release_id}).status_code == 201
    assert other_api.delete(path).status_code == 403

    # A member may leave; removing someone else needs the owner.
    LibraryMember.objects.create(
        library=library, user=User.objects.create_user("carol", password="x")
    )
    carol = LibraryMember.objects.get(user__username="carol")
    assert other_api.delete(f"{path}/members/{carol.pk}").status_code == 403
    assert other_api.delete(f"{path}/members/{member_id}").status_code == 204
    assert api.delete(f"{path}/members/{carol.pk}").status_code == 204
    assert str(library) == "Games"
    assert other_api.get("/libraries").json() == []


def test_member_str(library: Library, other: User) -> None:
    member = LibraryMember.objects.create(library=library, user=other)
    assert str(member) == "bob @ Games (viewer)"


def test_delete_library_with_loans(
    api: Any, library: Library, make_release: Callable[..., Release], switch: Platform
) -> None:
    """Loans keep their borrower from being deleted alone, not with the whole library."""
    item = Item.objects.create(library=library, release=make_release("Pikmin 4", switch))
    max_ = Person.objects.create(library=library, name="Max")
    Loan.objects.create(item=item, borrower=max_, lent_on=datetime.date(2026, 10, 1))
    assert api.delete(f"/libraries/{library.pk}/people/{max_.pk}").status_code == 409

    assert api.delete(f"/libraries/{library.pk}").status_code == 204
    assert not Library.objects.filter(pk=library.pk).exists()
    assert not Loan.objects.exists()
    assert not Person.objects.exists()
