"""Series and franchises described by Wikipedia: found through the games and series that
point to them, linked to each other."""

from typing import Any

import httpx
import pytest
from django.core.cache import cache

from apps.catalog.models import Franchise, Series
from apps.providers.services.integrations import save
from apps.providers.sources.wikipedia import WikipediaSource

from .fakes import host, response, router


def claim(value: Any) -> dict[str, Any]:
    return {"rank": "normal", "mainsnak": {"datavalue": {"value": value}}}


def item(*classes: str, **links: str) -> dict[str, Any]:
    claims = {"P31": [claim({"id": c}) for c in classes]}
    claims.update({prop: [claim({"id": qid})] for prop, qid in links.items()})
    return {"claims": claims}


WARS = {  # the series, filed under another name
    **item("Q7058673", P8345="Q50"),
    "sitelinks": {"dewiki": {"title": "Wars (Spieleserie)"}},
    "labels": {"en": {"value": "Wars"}},
}
GAME = {  # a game of it: part of the series
    **item("Q7889", P179="Q20"),
    "sitelinks": {"dewiki": {"title": "Advance Wars"}},
    "labels": {"en": {"value": "Advance Wars"}},
}
NAME = {"claims": {}, "sitelinks": {"dewiki": {"title": "Advance (Name)"}}}
FRANCHISE = {  # a "video game franchise", only with an English article
    **item("Q141546978"),
    "sitelinks": {"enwiki": {"title": "Nintendo Wars"}},
    "labels": {"en": {"value": "Nintendo Wars"}, "mul": {"value": "Wars franchise"}},
}
SERIES_TOO = {  # the same name as a series, with a German article
    **item("Q7058673"),
    "sitelinks": {"dewiki": {"title": "Nintendo Wars (Serie)"}},
    "labels": {"de": {"value": "Nintendo Wars"}},
}
LOGO_ONLY = {**item("Q7058673"), "claims": {**item("Q7058673")["claims"], "P154": [claim("W.svg")]}}
ITEMS = {
    "Q10": GAME,
    "Q11": NAME,
    "Q20": WARS,
    "Q50": FRANCHISE,
    "Q51": SERIES_TOO,
    "Q60": LOGO_ONLY,
}
LABELS = {"Q50": {"mul": {"value": "Nintendo Wars"}}}


@pytest.fixture
def wikidata(db: None, monkeypatch: pytest.MonkeyPatch) -> list[dict[str, str]]:
    """Searching "Advance Wars" finds a game and a name – in German and in English;
    "Nintendo Wars" finds the franchise and a series of that name."""
    save("wikipedia", enabled=True)
    cache.clear()
    calls: list[dict[str, str]] = []

    def answer(url: str, params: dict[str, str], **kwargs: Any) -> httpx.Response:
        calls.append(params)
        if params["action"] == "wbsearchentities":
            found = {
                "advance wars": ["Q10", "Q11"],
                "nintendo wars": ["Q51", "Q50"],
            }.get(params["search"].lower(), [])
            hits = [{"id": q, "label": params["search"], "description": "x"} for q in found]
            return response(json={"search": hits})
        ids = params["ids"].split("|")
        if params["props"] == "labels":
            return response(json={"entities": {q: {"labels": LABELS.get(q, {})} for q in ids}})
        return response(json={"entities": {q: ITEMS[q] for q in ids if q in ITEMS}})

    def wiki(url: str, params: dict[str, str], **kwargs: Any) -> httpx.Response:
        calls.append(params)
        titles = params["titles"].split("|")
        if params["prop"] == "pageprops":  # only "Wars (Computerspielreihe)" exists
            pages: list[dict[str, object]] = [
                {"title": t, "pageprops": {"wikibase_item": "Q20"}}
                if t == "Wars (Computerspielreihe)" and "de." in url
                else {"title": t, "missing": True}
                for t in titles
            ]
            return response(json={"query": {"pages": pages}})
        extracts = [{"title": t, "extract": f"Über {t}."} for t in titles]
        return response(json={"query": {"pages": extracts}})

    monkeypatch.setattr(
        "httpx.get",
        router(
            {
                "https://www.wikidata.org": answer,
                "https://de.wikipedia.org": wiki,
                "https://en.wikipedia.org": wiki,
            }
        ),
    )
    return calls


def test_a_series_found_through_its_games(wikidata: list[dict[str, str]]) -> None:
    found = WikipediaSource().describe("Advance Wars", "series", "de")
    assert found[0].external_id == "Q20"
    assert found[0].title == "Wars"
    # Searched in German, then in English, then the series the game points to.
    searches = [c["language"] for c in wikidata if c["action"] == "wbsearchentities"]
    assert searches == ["de", "en"]


def test_franchise_before_series_of_the_same_name(wikidata: list[dict[str, str]]) -> None:
    source = WikipediaSource()
    franchises = source.describe("Nintendo Wars", "franchises", "de")
    assert [(r.external_id, r.confident) for r in franchises] == [("Q50", True), ("Q51", True)]
    series = source.describe("Nintendo Wars", "series", "de")
    assert [r.external_id for r in series] == ["Q51", "Q50"]


def test_series_takes_its_franchise(api: Any, wikidata: list[dict[str, str]]) -> None:
    wars = Series.objects.create(name="Advance Wars")
    franchise = Franchise.objects.create(name="nintendo wars")
    record = WikipediaSource().description("Q20", "de", "series")
    assert record is not None
    assert record.franchise is not None
    assert record.franchise.names == ("Nintendo Wars",)  # the label for every language

    url = f"/catalog/series/{wars.pk}/description/wikipedia"
    assert api.post(url, {"external_id": "Q20"}).status_code == 200
    wars.refresh_from_db()
    assert wars.franchise == franchise
    assert wars.descriptions["de"].startswith("Über Wars")
    detail = api.get(f"/catalog/series/{wars.pk}").json()
    assert detail["franchise"] == {"id": str(franchise.pk), "name": "nintendo wars"}
    assert api.get(f"/catalog/franchises/{franchise.pk}").json()["parts"] == [
        {"id": str(wars.pk), "name": "Advance Wars"}
    ]

    # A franchise chosen by hand stays; franchises are described too.
    other = Franchise.objects.create(name="Other")
    wars.franchise = other
    wars.save()
    api.post(url, {"external_id": "Q20"})
    wars.refresh_from_db()
    assert wars.franchise == other
    url = f"/catalog/franchises/{franchise.pk}/description/wikipedia"
    assert api.post(url, {"external_id": "Q50"}).status_code == 200
    franchise.refresh_from_db()
    assert franchise.external_ids == {"wikipedia": "Q50"}
    assert franchise.descriptions == {
        "en": "Über Nintendo Wars.\n\nSource: Wikipedia, CC BY-SA 4.0"
    }


def test_series_franchise_by_hand_and_merges(api: Any, db: None) -> None:
    wars = Series.objects.create(name="Advance Wars")
    copy = Series.objects.create(name="Advance Wars (copy)")
    nintendo = Franchise.objects.create(name="Nintendo Wars")
    old = Franchise.objects.create(name="Wars")
    path = f"/catalog/series/{wars.pk}"
    answer = api.patch(path, {"series": {"franchise": {"id": str(old.pk)}}}).json()
    assert answer["franchise"]["name"] == "Wars"
    copy.franchise = nintendo
    copy.save()
    # Merging franchises moves their series; a merged series keeps a franchise.
    api.post(f"/catalog/franchises/{old.pk}/merge", {"target_id": str(nintendo.pk)})
    wars.refresh_from_db()
    assert wars.franchise == nintendo
    wars.franchise = None
    wars.save()
    api.post(f"/catalog/series/{copy.pk}/merge", {"target_id": str(wars.pk)})
    wars = Series.objects.get(pk=wars.pk)
    assert wars.franchise == nintendo
    assert api.patch(path, {"series": {"franchise": None}}).json()["franchise"] is None
    # Only series belong to a franchise.
    bad = api.patch(f"/catalog/franchises/{nintendo.pk}", {"series": {"franchise": None}})
    assert bad.status_code == 400


def test_an_entry_with_only_a_logo(
    api: Any, wikidata: list[dict[str, str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """No article, but a logo: the entry is remembered and its logo taken."""
    inner = httpx.get
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0h1v1z"/></svg>'

    def get(url: str, *args: Any, **kwargs: Any) -> httpx.Response:
        if host(url) == "upload.wikimedia.org":
            return response(content=svg, ctype="image/svg+xml")
        return inner(url, *args, **kwargs)

    monkeypatch.setattr("httpx.get", get)
    wars = Series.objects.create(name="Wars")
    url = f"/catalog/series/{wars.pk}/description/wikipedia"
    assert api.post(url, {"external_id": "Q60", "image": True}).json()["image"] is True
    wars.refresh_from_db()
    assert wars.external_ids == {"wikipedia": "Q60"}
    assert wars.descriptions == {}
    assert wars.image.read() == svg


def test_a_series_found_by_its_article_title(wikidata: list[dict[str, str]]) -> None:
    """ "Wars" finds nothing on Wikidata; the article "Wars (Computerspielreihe)" is it."""
    found = WikipediaSource().describe("Wars", "series", "de")
    assert [(r.external_id, r.confident) for r in found] == [("Q20", True)]
    asked = [c["titles"] for c in wikidata if c.get("prop") == "pageprops"]
    assert asked[0].startswith("Wars (Computerspielreihe)|")
    assert len(asked) == 2
