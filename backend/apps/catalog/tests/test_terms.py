from collections.abc import Callable
from pathlib import Path
from typing import Any

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.catalog.models import Company, Genre, Platform, Release, Series
from apps.catalog.services.terms import by_name
from apps.catalog.tests.test_platforms import SVG, png

UNKNOWN = "00000000-0000-0000-0000-000000000000"


def test_suggestions_rank_prefix_first_then_use(
    api: Any, make_release: Callable[..., Release], switch: Platform
) -> None:
    make_release("A", switch, publisher="Nintendo", developers=("Nintendo EPD",))
    make_release("B", switch, publisher="Nintendo")
    make_release("C", switch, developers=("Monolith Soft", "Next Level Games"))
    found = api.get("/catalog/companies", {"q": "n"}).json()
    names = [c["name"] for c in found]
    # Starting with "n" first (most used first), then those only containing it.
    assert names[:3] == ["Nintendo", "Next Level Games", "Nintendo EPD"]
    assert names[3:] == ["Monolith Soft"]
    assert found[0]["uses"] == 2  # published two releases
    assert len(api.get("/catalog/companies", {"limit": 1}).json()) == 1

    make_release("D", switch, genres=("Puzzle",))
    assert [g["name"] for g in api.get("/catalog/genres", {"q": "puz"}).json()] == ["Puzzle"]
    zelda = Series.objects.create(name="The Legend of Zelda")
    zelda.works.add(Release.objects.get(work__title="A").work)
    series = api.get("/catalog/series", {"q": "legend"}).json()
    assert series == [
        {
            "id": str(zelda.pk),
            "name": "The Legend of Zelda",
            "uses": 1,
            "image_url": None,
            "image_tone": "",
            "summary": "",
            "country": "",
            "founded": None,
        }
    ]


def test_edition_suggestions(
    api: Any, make_release: Callable[..., Release], switch: Platform
) -> None:
    for title, edition in (("A", "Deluxe Edition"), ("B", "Deluxe Edition"), ("C", "Steelbook")):
        release = make_release(title, switch)
        release.edition = edition
        release.save()
    make_release("D", switch)  # no edition: not suggested
    assert api.get("/catalog/editions").json() == [
        {"name": "Deluxe Edition", "uses": 2},
        {"name": "Steelbook", "uses": 1},
    ]
    assert api.get("/catalog/editions", {"q": "steel"}).json() == [{"name": "Steelbook", "uses": 1}]
    # An edition typed with stray spaces is stored clean.
    release = Release.objects.get(work__title="D")
    patched = api.patch(f"/catalog/releases/{release.pk}", {"edition": "  Gold   Edition "})
    assert patched.json()["edition"] == "Gold Edition"


def test_picking_terms(api: Any, make_release: Callable[..., Release], switch: Platform) -> None:
    release = make_release("Pikmin", switch, publisher="Nintendo")
    nintendo = Company.objects.get(name="Nintendo")
    work_url = f"/catalog/works/{release.work_id}"
    # Existing ones by id, new ones by name – a name in another case is the existing one.
    body = api.patch(
        work_url,
        {"developers": [{"id": str(nintendo.pk)}, {"name": "nintendo"}, {"name": "Monolith"}]},
    ).json()
    assert [d["name"] for d in body["developers"]] == ["Monolith", "Nintendo"]
    assert Company.objects.filter(name__iexact="nintendo").count() == 1
    assert api.patch(work_url, {"genres": [{"id": UNKNOWN}]}).status_code == 400
    # Blank names are ignored.
    assert api.patch(work_url, {"series": [{"name": "  "}]}).json()["series"] == []

    url = f"/catalog/releases/{release.pk}"
    assert api.patch(url, {"publisher": {"name": "NINTENDO"}}).json()["publisher"]["name"] == (
        "Nintendo"
    )
    # Leaving the publisher out keeps it; null removes it.
    assert api.patch(url, {"age_rating": "USK 0"}).json()["publisher"]["name"] == "Nintendo"
    assert api.patch(url, {"publisher": None}).json()["publisher"] is None


def test_term_page_lists_games(
    api: Any, make_release: Callable[..., Release], switch: Platform, nds: Platform
) -> None:
    pikmin = make_release(
        "Pikmin", switch, year=2001, publisher="Nintendo", developers=("Nintendo EPD",)
    )
    Release.objects.create(work=pikmin.work, platform=nds, publisher=pikmin.publisher)
    make_release("Metroid", switch, year=1986, publisher="Nintendo", genres=("Action",))
    nintendo = Company.objects.get(name="Nintendo")
    page = api.get(f"/catalog/companies/{nintendo.pk}").json()
    assert (page["name"], page["description"], page["image_url"]) == ("Nintendo", "", None)
    assert page["works"] == []  # developed nothing
    # Oldest first, each with its platforms (oldest first) and year.
    assert [(w["title"], w["year"]) for w in page["published"]] == [
        ("Metroid", 1986),
        ("Pikmin", 2001),
    ]
    assert [p["slug"] for p in page["published"][1]["platforms"]] == ["nds", "switch"]
    assert page["published"][1]["cover_url"] is None
    # What these games have in common besides Nintendo.
    assert [(r["kind"], r["name"], r["count"]) for r in page["related"]] == [
        ("genres", "Action", 1),
        ("companies", "Nintendo EPD", 1),
    ]
    epd = Company.objects.get(name="Nintendo EPD")
    assert [w["title"] for w in api.get(f"/catalog/companies/{epd.pk}").json()["works"]] == [
        "Pikmin"
    ]
    action = Genre.objects.get(name="Action")
    genre = api.get(f"/catalog/genres/{action.pk}").json()
    assert [w["title"] for w in genre["works"]] == ["Metroid"]
    assert (genre["published"], genre["related"]) == ([], [])
    zelda = Series.objects.create(name="Zelda")
    assert api.get(f"/catalog/series/{zelda.pk}").json()["works"] == []
    assert api.get(f"/catalog/series/{UNKNOWN}").status_code == 404
    assert api.get(f"/catalog/companies/{action.pk}").status_code == 404  # wrong kind


def test_description_and_image(api: Any) -> None:
    capcom = Company.objects.create(name="Capcom")
    path = f"/catalog/companies/{capcom.pk}"
    page = api.patch(path, {"descriptions": {"en": "  Osaka.  "}}).json()
    # No German text (the tests' language): the English one stands in.
    assert (page["name"], page["description"], page["description_language"]) == (
        "Capcom",
        "Osaka.",
        "en",
    )
    page = api.patch(path, {"descriptions": {"de": "Ōsaka."}}).json()
    assert (page["description"], page["description_language"]) == ("Ōsaka.", "de")
    assert page["descriptions"] == {"en": "Osaka.", "de": "Ōsaka."}
    # An empty text removes its language; unknown languages are refused.
    page = api.patch(path, {"descriptions": {"de": " "}}).json()
    assert page["descriptions"] == {"en": "Osaka."}
    assert api.patch(path, {"descriptions": {"fr": "Osaka"}}).status_code == 400

    def upload(content: bytes, name: str) -> Any:
        return api.client.post(f"/api{path}/image", {"file": SimpleUploadedFile(name, content)})

    assert upload(b"<svg><script>x</script></svg>", "a.svg").status_code == 400
    assert upload(b"x" * (2049 * 1024), "big.png").status_code == 400
    first = upload(SVG, "logo.svg").json()["image_url"]
    assert first.startswith("/media/terms/company/")
    assert first.endswith(".svg")
    second = upload(png(), "logo.png").json()["image_url"]
    assert second != first
    assert second.endswith(".png")
    capcom.refresh_from_db()
    stored = Path(capcom.image.path)
    assert stored.exists()
    assert not any(stored.parent.glob("*.svg"))  # the old one is gone
    assert api.get("/catalog/companies", {"q": "cap"}).json()[0]["image_url"] == second
    # How it reads is measured with it: a black glyph is inverted on dark pages.
    glyph = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0h9v9z"/></svg>'
    assert upload(glyph, "glyph.svg").json()["image_tone"] == "black"
    assert api.get("/catalog/companies", {"q": "cap"}).json()[0]["image_tone"] == "black"
    capcom.refresh_from_db()
    stored = Path(capcom.image.path)
    removed = api.delete(f"{path}/image").json()
    assert (removed["image_url"], removed["image_tone"]) == (None, "")
    assert not stored.exists()
    upload(png(), "logo.png")
    capcom.refresh_from_db()
    stored = Path(capcom.image.path)
    assert api.delete(path).status_code == 204
    assert not stored.exists()  # deleting the entry deletes its picture


def test_rename_merge_delete(
    api: Any, make_release: Callable[..., Release], switch: Platform
) -> None:
    a = make_release("A", switch, publisher="Nintnedo", developers=("Nintnedo", "EPD"))
    b = make_release("B", switch, publisher="Nintendo", developers=("Nintendo",))
    make_release("C", switch, developers=("EPD",))
    typo = Company.objects.get(name="Nintnedo")
    b.developers.add(typo)  # worked on this release only
    nintendo = Company.objects.get(name="Nintendo")
    nintendo.external_ids = {"igdb": 70}
    typo.external_ids = {"igdb": 1, "mobygames": 9}
    typo.descriptions = {"de": "Kyoto.", "en": "Kyoto (en)."}
    nintendo.descriptions = {"en": "Nintendo."}
    typo.image.save("logo.svg", ContentFile(SVG), save=False)
    typo.save()
    nintendo.save()
    image = Path(typo.image.path)

    # Renaming to a name that exists (in any case) asks for a merge instead.
    clash = api.patch(f"/catalog/companies/{typo.pk}", {"name": "  nintendo "})
    assert clash.status_code == 409
    assert "nintendo" in clash.json()["detail"]
    assert api.patch(f"/catalog/companies/{typo.pk}", {"name": " "}).status_code == 400
    renamed = api.patch(f"/catalog/companies/{typo.pk}", {"name": "Nintendo  Co."}).json()
    assert (renamed["id"], renamed["name"]) == (str(typo.pk), "Nintendo Co.")

    merged = api.post(f"/catalog/companies/{typo.pk}/merge", {"target_id": str(nintendo.pk)})
    assert merged.json() == {"id": str(nintendo.pk), "name": "Nintendo"}
    assert not Company.objects.filter(pk=typo.pk).exists()
    a.refresh_from_db()
    assert a.publisher == nintendo
    assert [d.name for d in a.work.developers.order_by("name")] == ["EPD", "Nintendo"]
    assert [d.name for d in b.work.developers.all()] == ["Nintendo"]
    assert [d.name for d in b.developers.all()] == ["Nintendo"]
    nintendo.refresh_from_db()
    assert nintendo.external_ids == {"igdb": 70, "mobygames": 9}  # the target's win
    # What the target lacked it takes over, the picture's file included.
    assert nintendo.descriptions == {"de": "Kyoto.", "en": "Nintendo."}
    assert Path(nintendo.image.path) == image
    assert image.exists()
    itself = api.post(f"/catalog/companies/{nintendo.pk}/merge", {"target_id": str(nintendo.pk)})
    assert itself.status_code == 400

    # Genres and series merge the same way, without doubling a game's link.
    make_release("D", switch, genres=("RPG", "Role-playing"))
    rpg, role = Genre.objects.get(name="RPG"), Genre.objects.get(name="Role-playing")
    api.post(f"/catalog/genres/{rpg.pk}/merge", {"target_id": str(role.pk)})
    assert list(Genre.objects.values_list("name", flat=True)) == ["Role-playing"]
    one, two = Series.objects.create(name="Zelda"), Series.objects.create(name="Legend of Zelda")
    one.works.add(a.work)
    two.works.add(a.work, b.work)
    api.post(f"/catalog/series/{one.pk}/merge", {"target_id": str(two.pk)})
    assert two.works.count() == 2

    # Deleting leaves the games without it.
    assert api.delete(f"/catalog/companies/{nintendo.pk}").status_code == 204
    a = Release.objects.get(pk=a.pk)
    assert a.publisher is None
    assert [d.name for d in a.work.developers.all()] == ["EPD"]


def test_long_names(api: Any) -> None:
    """A name longer than the field finds its (cut) term the second time instead of
    clashing with it; a rename that long is refused."""
    long = "Action " * 20  # > 100, the genre name's max_length
    first = by_name(Genre, long)
    assert first is not None
    assert len(first.name) <= 100
    assert by_name(Genre, long.upper()) == first
    assert Genre.objects.count() == 1
    response = api.patch(f"/catalog/genres/{first.pk}", {"name": "x" * 101})
    assert response.status_code == 400
    assert api.patch(f"/catalog/genres/{first.pk}", {"name": "x" * 100}).status_code == 200


def test_edition_limit_is_bounded(api: Any) -> None:
    assert api.get("/catalog/editions", {"limit": -1}).status_code == 200


def test_company_details(api: Any) -> None:
    capcom = Company.objects.create(name="Capcom")
    path = f"/catalog/companies/{capcom.pk}"
    assert api.get(path).json()["company"] == {
        "founded": None,
        "dissolved": None,
        "country": "",
        "headquarters": "",
        "website": "",
        "parent": None,
        "subsidiaries": [],
    }
    details = {
        "founded": 1979,
        "country": " jp ",
        "headquarters": "  Osaka ",
        "website": "https://www.capcom.co.jp",
        "parent": {"name": "Capcom Holdings"},  # a new one by name
    }
    page = api.patch(path, {"company": details}).json()
    company = page["company"]
    assert (company["founded"], company["country"], company["headquarters"]) == (
        1979,
        "JP",
        "Osaka",
    )
    holdings = Company.objects.get(name="Capcom Holdings")
    assert company["parent"] == {"id": str(holdings.pk), "name": "Capcom Holdings"}
    holding_page = api.get(f"/catalog/companies/{holdings.pk}").json()["company"]
    assert holding_page["subsidiaries"] == [{"id": str(capcom.pk), "name": "Capcom"}]

    for bad in (
        {"website": "javascript:alert(1)"},
        {"country": "Japan"},
        {"founded": 79},
        {"founded": 2000, "dissolved": 1999},
        {"parent": {"id": str(capcom.pk)}},  # itself
    ):
        assert api.patch(path, {"company": bad}).status_code == 400, bad
    # A loop further up.
    loop = {"parent": {"id": str(capcom.pk)}}
    assert api.patch(f"/catalog/companies/{holdings.pk}", {"company": loop}).status_code == 400
    # Only companies have them.
    action = Genre.objects.create(name="Action")
    assert api.patch(f"/catalog/genres/{action.pk}", {"company": {}}).status_code == 400
    assert api.get(f"/catalog/genres/{action.pk}").json()["company"] is None
    # Everything at once: an empty form clears them.
    assert api.patch(path, {"company": {}}).json()["company"]["parent"] is None


def test_merging_companies_keeps_details(db: None) -> None:
    from apps.catalog.services.terms import merge

    parent = Company.objects.create(name="Sega Sammy")
    sega = Company.objects.create(name="Sega", founded=1960, country="JP", parent=parent)
    typo = Company.objects.create(name="SEGA Corp", website="https://sega.com")
    child = Company.objects.create(name="Atlus", parent=typo)
    merge(typo, sega)
    sega.refresh_from_db()
    child.refresh_from_db()
    assert (sega.founded, sega.website, sega.parent) == (1960, "https://sega.com", parent)
    assert child.parent == sega
    # Merging a company into its own parent: no parent of itself afterwards.
    merge(sega, parent)
    parent.refresh_from_db()
    child.refresh_from_db()
    assert parent.parent is None
    assert child.parent == parent


def test_overview_entries(api: Any, db: None) -> None:
    from apps.catalog.models import Company

    Company.objects.create(
        name="Nintendo",
        country="JP",
        founded=1889,
        descriptions={"en": "Kyoto.\nMore.", "de": "x" * 200},
    )
    entry = api.get("/catalog/companies", {"q": "nintendo"}).json()[0]
    assert (entry["country"], entry["founded"]) == ("JP", 1889)
    assert entry["summary"] == "x" * 139 + "…"  # German: the reader's language
