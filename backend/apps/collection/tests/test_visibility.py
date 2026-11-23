"""What a library's viewers see: no contact details, no money; loans as the owner chooses."""

import datetime
from decimal import Decimal
from typing import Any

import pytest

from apps.accounts.models import User
from apps.catalog.models import Release
from apps.collection.models import Item, Library, LibraryMember, Loan, Person, Role


@pytest.fixture
def shared(library: Library, stocked: dict[str, Item], other: User) -> dict[str, Any]:
    """bob views alice's library; Zelda is lent to Carol, all copies have prices."""
    LibraryMember.objects.create(library=library, user=other, role=Role.VIEWER)
    carol = Person.objects.create(library=library, name="Carol", email="c@x.org", notes="nice")
    owner = Person.objects.create(library=library, name="Alice")
    for item in stocked.values():
        item.purchase_price, item.current_value, item.owner = Decimal(50), Decimal(30), owner
        item.save()
    Loan.objects.create(item=stocked["zelda"], borrower=carol, lent_on=datetime.date(2026, 1, 2))
    return {"library": library, "items": stocked}


def test_viewers_see_no_money_contacts_or_borrowers(
    other_api: Any, api: Any, shared: dict[str, Any]
) -> None:
    lib = f"/libraries/{shared['library'].pk}"
    zelda = shared["items"]["zelda"]
    listed = other_api.get(f"{lib}/items").json()["items"]
    assert {(i["purchase_price"], i["current_value"]) for i in listed} == {(None, None)}
    # Who owns a copy stays visible.
    assert {i["owner"]["name"] for i in listed} == {"Alice"}
    lent = next(i for i in listed if i["id"] == str(zelda.pk))
    # Default: viewers learn that it is lent, not to whom or since when.
    assert lent["active_loan"]["borrower"] is None
    assert lent["active_loan"]["lent_on"] is None
    assert other_api.get(f"{lib}/items/{zelda.pk}").json()["current_value"] is None
    assert other_api.get(f"/items/{zelda.pk}").json()["purchase_price"] is None
    assert other_api.get(f"{lib}/tree").json()["total_value"] == "0"
    people = other_api.get(f"{lib}/people").json()
    assert {(p["name"], p["email"], p["notes"]) for p in people} == {
        ("Carol", "", ""),
        ("Alice", "", ""),
    }
    assert other_api.get(f"{lib}/loans").status_code == 403
    # Grouping, sorting and filtering by hidden fields is ignored, not answered.
    tree = other_api.get(f"{lib}/tree", {"group_by": ["loan.to", "release.year"]}).json()
    assert [n["field"] for n in tree["nodes"]] == ["release.year", "release.year"]
    assert other_api.get(f"{lib}/items", {"where": "copy.price>=40"}).json()["count"] == 3
    assert other_api.get(f"{lib}/items", {"filter": "loan.to:x"}).json()["count"] == 3
    assert other_api.get(f"{lib}/items", {"sort": "-copy.value"}).status_code == 200
    assert other_api.get(f"{lib}/items", {"section": "loan.to"}).json()["sections"] == []

    # The owner may hide loans from viewers entirely; editors and owners see everything.
    assert api.patch(lib, {"viewer_loans": "hidden"}).json()["viewer_loans"] == "hidden"
    hidden = other_api.get(f"{lib}/items/{zelda.pk}").json()
    assert hidden["active_loan"] is None
    own = api.get(f"{lib}/items/{zelda.pk}").json()
    assert own["active_loan"]["borrower"]["name"] == "Carol"
    assert own["current_value"] == "30.00"
    assert api.get(f"{lib}/tree").json()["total_value"] == "90.00"
    assert {p["email"] for p in api.get(f"{lib}/people").json()} == {"c@x.org", ""}
    assert other_api.patch(lib, {"viewer_loans": "status"}).status_code == 403
    assert api.patch(lib, {"name": " "}).status_code == 400


def test_upcoming_needs_editing_rights_to_share_and_hides_details(
    other_api: Any, api: Any, shared: dict[str, Any], user: User
) -> None:
    library = shared["library"]
    release: Release = shared["items"]["sonic"].release
    entry = {"release_id": str(release.pk), "library_id": str(library.pk), "price": "60"}
    assert other_api.post("/watchlist", entry).status_code == 403
    LibraryMember.objects.filter(library=library).update(role=Role.EDITOR)
    created = other_api.post("/watchlist", {**entry, "shop": "Shop", "notes": "gift"})
    assert created.status_code == 201
    seen = next(e for e in api.get("/watchlist").json() if e["user"] == "bob")
    assert (seen["shop"], seen["price"], seen["notes"]) == ("", None, "")
    mine = other_api.get("/watchlist").json()[0]
    assert (mine["shop"], mine["price"]) == ("Shop", "60.00")
