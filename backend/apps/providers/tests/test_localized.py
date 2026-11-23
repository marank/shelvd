"""Game data in the reader's language: IGDB's localized titles and genres, Wikipedia."""

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from django.core.cache import cache

from apps.catalog.models import Platform, Release, Work
from apps.providers.services.integrations import save
from apps.providers.sources import ProviderError, metadata_source, metadata_sources
from apps.providers.sources.base import CompanyFacts, EntryRef
from apps.providers.sources.igdb import IGDBSource
from apps.providers.sources.wikipedia import WikipediaSource

from .fakes import IGDB_GAME, host, response, router

GERMAN = {
    **IGDB_GAME,
    "alternative_names": [
        {"name": "スーパーマリオ オデッセイ", "comment": "Japanese title - original"},
        {"name": "Super Mario Odyssee", "comment": "German title"},
    ],
    "genres": [{"name": "Platform"}, {"name": "Role-playing (RPG)"}, {"name": "New"}],
}


def entity(qid: str, title: str | None, classes: tuple[str, ...] = ("Q7889",)) -> dict[str, Any]:
    claims: dict[str, Any] = {
        "P31": [{"mainsnak": {"datavalue": {"value": {"id": c}}}} for c in classes],
        "P577": [
            {
                "mainsnak": {
                    "datavalue": {"value": {"time": "+2017-10-27T00:00:00Z", "precision": 11}}
                }
            },
            {
                "mainsnak": {
                    "datavalue": {"value": {"time": "+2017-00-00T00:00:00Z", "precision": 9}}
                }
            },
            {"mainsnak": {"datavalue": {"value": {"time": "+bogus", "precision": 11}}}},
            {"mainsnak": {}},
        ],
    }
    sitelinks = {"dewiki": {"title": title}} if title else {}
    return {"claims": claims, "sitelinks": sitelinks}


ENTITIES = {
    "Q1": entity("Q1", "Super Mario Odyssey (Videospiel)"),
    "Q2": entity("Q2", "Mario (Figur)", classes=("Q15632617",)),  # not a game
    "Q3": entity("Q3", None),  # no German article
    "Q4": {"claims": {"P5794": [{}]}, "sitelinks": {"dewiki": {"title": "Odyssey"}}},
}


@pytest.fixture
def wikipedia(db: None, monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Wikidata knows four items, one of them a game with a German article; returns the
    parameters of every request."""
    save("wikipedia", enabled=True)
    calls: list[dict[str, Any]] = []

    def wikidata(url: str, params: dict[str, str], **kwargs: Any) -> httpx.Response:
        calls.append(params)
        assert kwargs["headers"]["User-Agent"].startswith("shelvd/")
        if params["action"] == "wbsearchentities":
            return response(json={"search": [{"id": q} for q in ("Q1", "Q2", "Q3", "Q4")] + [{}]})
        ids = params["ids"].split("|")
        return response(json={"entities": {q: ENTITIES[q] for q in ids if q in ENTITIES}})

    def wiki(url: str, params: dict[str, str], **kwargs: Any) -> httpx.Response:
        calls.append(params)
        return response(
            json={
                "query": {
                    "pages": [
                        {"title": "Super Mario Odyssey (Videospiel)", "extract": " Mit Cappy. "},
                        {"title": "Odyssey"},
                        {},
                    ]
                }
            }
        )

    monkeypatch.setattr(
        "httpx.get",
        router({"https://www.wikidata.org": wikidata, "https://de.wikipedia.org": wiki}),
    )
    return calls


def test_igdb_titles_and_genres_in_the_language(db: None) -> None:
    source = IGDBSource()
    german = source._records(GERMAN, None, "de")[0]
    assert german.title == "Super Mario Odyssee"
    assert german.genres == ["Jump 'n' Run", "Rollenspiel", "New"]
    english = source._records(GERMAN, None, "en-GB")[0]
    assert english.title == "Super Mario Odyssey"
    assert english.genres == ["Platform", "Role-playing (RPG)", "New"]
    # No German title listed: IGDB's own.
    assert source._records(IGDB_GAME, None, "de")[0].title == "Super Mario Odyssey"


def test_wikipedia_finds_games_with_an_article(wikipedia: list[dict[str, Any]]) -> None:
    source = WikipediaSource()
    assert source.catalog is False
    assert "summary" in source.fields
    found = source.search("Mario", language="de-DE")
    assert [(r.external_id, r.title) for r in found] == [
        ("Q1", "Super Mario Odyssey"),
        ("Q4", "Odyssey"),
    ]
    assert found[0].summary == "Mit Cappy.\n\nQuelle: Wikipedia, CC BY-SA 4.0"
    assert found[0].first_release_date
    assert found[0].first_release_date.isoformat() == "2017-10-27"
    assert found[1].summary == ""
    assert found[1].first_release_date is None
    assert wikipedia[0]["language"] == "de"
    assert wikipedia[1]["sitefilter"] == "dewiki"

    record = source.get("Q1", language="de")
    assert record is not None
    assert record.title == "Super Mario Odyssey"
    assert source.get("Q2", language="de") is None
    assert source.get_all("not an id") == []


def test_wikipedia_unknown_languages_and_nothing_found(
    db: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str] = []

    def nothing(url: str, params: dict[str, str], **kwargs: Any) -> httpx.Response:
        seen.append(params.get("language", ""))
        return response(json={"search": []})

    monkeypatch.setattr("httpx.get", router({"https://www.wikidata.org": nothing}))
    assert WikipediaSource().search("Mario", language="fr") == []
    assert seen == ["en"]
    assert WikipediaSource().describe("Mario", "companies", "fr") == []
    assert WikipediaSource().test() == "OK"


@pytest.mark.parametrize(
    "answer",
    [
        lambda *a, **k: response(500, json={}),
        lambda *a, **k: response(json={"error": {"code": "badvalue"}}),
        lambda *a, **k: response(content=b"<html>", ctype="text/html"),
    ],
)
def test_wikipedia_errors(
    db: None, monkeypatch: pytest.MonkeyPatch, answer: Callable[..., httpx.Response]
) -> None:
    monkeypatch.setattr("httpx.get", router({"https://www.wikidata.org": answer}))
    with pytest.raises(ProviderError):
        WikipediaSource().search("Mario")


def test_wikipedia_only_completes_games(db: None) -> None:
    save("igdb", enabled=True, secrets={"client_id": "id", "client_secret": "secret"})
    save("wikipedia", enabled=True)
    cache.clear()
    assert [s.name for s in metadata_sources()] == ["igdb", "wikipedia"]
    assert [s.name for s in metadata_sources(catalog=True)] == ["igdb"]
    assert metadata_source("wikipedia", catalog=True) is None


def test_match_with_wikipedia(
    api: Any,
    wikipedia: list[dict[str, Any]],
    make_release: Callable[..., Release],
    switch: Platform,
) -> None:
    release = make_release("Mario Odyssey", switch)
    url = f"/catalog/works/{release.work_id}/metadata/wikipedia"
    found = api.get(f"{url}/candidates").json()
    assert [c["external_id"] for c in found] == ["Q1", "Q4"]
    assert found[0]["platforms"] == []
    assert found[0]["cover_url"] == ""

    changes = api.get(f"{url}/Q1").json()["changes"]
    assert {c["field"]: c["kind"] for c in changes} == {
        "title": "differs",
        "summary": "fill",
        "first_release_date": "fill",
    }
    api.post(url, {"external_id": "Q1", "changes": ["work.summary"]})
    work = Work.objects.get(pk=release.work_id)
    assert work.summary.startswith("Mit Cappy.")
    assert work.external_ids == {"wikipedia": "Q1"}


def test_import_needs_a_catalog_source(
    api: Any, wikipedia: list[dict[str, Any]], switch: Platform
) -> None:
    answer = api.post(
        "/lookup/import",
        {
            "provider": "wikipedia",
            "external_id": "Q1",
            "platform_id": str(switch.pk),
            "region": "pal",
        },
    )
    assert answer.status_code == 400


# --- descriptions of companies and series -----------------------------------------------
def _logo(value: Any, rank: str = "normal") -> dict[str, Any]:
    """A claim with this value."""
    return {"rank": rank, "mainsnak": {"datavalue": {"value": value}}}


LABELS = {
    "Q34600": {"de": {"value": "Kyōto"}, "en": {"value": "Kyoto"}},
    "Q90": {"en": {"value": "Nintendo Holdings"}},
    "Q91": {"de": {"value": "Monolith Soft"}},
    "Q92": {"de": {"value": "Retro Studios"}},
    "Q93": {},
}


COMPANY = {
    "claims": {
        "P31": [{"mainsnak": {"datavalue": {"value": {"id": "Q1137109"}}}}],
        "P154": [
            _logo("Old logo.png", "deprecated"),
            _logo("Nintendo 1970s.png"),
            _logo("Nintendo.svg", "preferred"),
        ],
        "P571": [
            _logo({"time": "+1947-00-00T00:00:00Z", "precision": 9}),
            _logo({"time": "+1889-09-23T00:00:00Z", "precision": 11}),
            _logo({"time": "+1800-00-00T00:00:00Z", "precision": 7}),  # century: ignored
        ],
        "P17": [_logo({"id": "Q17"})],
        "P159": [_logo({"id": "Q34600"}, "preferred")],
        "P856": [
            _logo("https://old.example", "deprecated"),
            _logo("ftp://nintendo.example"),
            _logo("https://www.nintendo.co.jp"),
        ],
        "P749": [_logo({"id": "Q90"})],
        "P355": [_logo({"id": "Q91"}), _logo({"id": "Q92"}), _logo({"id": "Q93"})],
    },
    "sitelinks": {"dewiki": {"title": "Nintendo"}, "enwiki": {"title": "Nintendo"}},
    "labels": {"de": {"value": "Nintendo"}},
}
# md5("Nintendo.svg") starts with 0d.
NINTENDO_LOGO = "https://upload.wikimedia.org/wikipedia/commons/0/0d/Nintendo.svg"
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>'
CONSOLE = {"claims": {}, "sitelinks": {"dewiki": {"title": "Nintendo Switch"}}}
GAME = {
    "claims": {"P31": [{"mainsnak": {"datavalue": {"value": {"id": "Q7889"}}}}]},
    "sitelinks": {"dewiki": {"title": "Nintendogs"}},
}
NO_TEXT = {"claims": {}, "sitelinks": {"dewiki": {"title": "Leer"}}}
# A games company (by its industry) without any article: facts only.
STUDIO = {"claims": {"P452": [_logo({"id": "Q941594"})]}, "sitelinks": {}}
# Something else, with an English article only.
MAGAZINE = {"claims": {}, "sitelinks": {"enwiki": {"title": "Nintendo Power (magazine)"}}}
# Neither a company nor with an article: left out.
NOTHING: dict[str, Any] = {"claims": {}, "sitelinks": {}}
SEARCH_LABELS = {"Q11": "Nintendo", "Q14": "Nintendo", "Q16": "Nintendo"}


@pytest.fixture
def described(db: None, monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    save("wikipedia", enabled=True)
    calls: list[dict[str, Any]] = []
    items = {
        "Q15": MAGAZINE,
        "Q14": STUDIO,
        "Q10": CONSOLE,
        "Q11": COMPANY,
        "Q12": GAME,
        "Q13": NO_TEXT,
        "Q16": NOTHING,
    }

    def wikidata(url: str, params: dict[str, str], **kwargs: Any) -> httpx.Response:
        calls.append(params)
        if params["action"] == "wbsearchentities":
            # Wikidata knows only these spellings.
            if params["search"].lower() not in {"nintendo", "big n"}:
                return response(json={"search": []})
            found = [
                {"id": q, "description": f"about {q}", "label": SEARCH_LABELS.get(q, q)}
                for q in items
            ]
            return response(json={"search": found})
        if params["action"] == "wbgetclaims":
            code = {"Q17": "jp"}.get(params["entity"])
            return response(json={"claims": {"P297": [_logo(code)] if code else []}})
        ids = params["ids"].split("|")
        if params["props"] == "labels":
            return response(json={"entities": {q: {"labels": LABELS[q]} for q in ids}})
        if any(q not in items for q in ids):
            return response(json={"entities": {q: {"id": q, "missing": ""} for q in ids}})
        return response(json={"entities": {q: items[q] for q in ids if q in items}})

    def wiki(texts: dict[str, str]) -> Callable[..., httpx.Response]:
        def answer(url: str, params: dict[str, str], **kwargs: Any) -> httpx.Response:
            titles = params["titles"].split("|")
            pages = [{"title": t, "extract": texts.get(t, "")} for t in titles]
            return response(json={"query": {"pages": pages}})

        return answer

    de = {"Nintendo": "Ein Unternehmen.", "Nintendo Switch": "Eine Konsole."}
    en = {"Nintendo": "A company.", "Nintendo Power (magazine)": "A magazine."}
    monkeypatch.setattr(
        "httpx.get",
        router(
            {
                "https://www.wikidata.org": wikidata,
                "https://de.wikipedia.org": wiki(de),
                "https://en.wikipedia.org": wiki(en),
            }
        ),
    )
    return calls


def test_describe_companies_first(described: list[dict[str, Any]]) -> None:
    source = WikipediaSource()
    found = source.describe("Nintendo", "companies", "de")
    # Companies with that name first – with an article before without –, then the rest
    # (a German article before an English one); games, empty articles and entries that
    # are neither a company nor have an article left out.
    assert [(r.external_id, r.confident, r.language) for r in found] == [
        ("Q11", True, "de"),
        ("Q14", True, ""),
        ("Q10", False, "de"),
        ("Q15", False, "en"),
    ]
    assert found[0].text == "Ein Unternehmen.\n\nQuelle: Wikipedia, CC BY-SA 4.0"
    assert (found[0].label, found[0].image_url) == ("about Q11", NINTENDO_LOGO)
    assert (found[1].title, found[1].text) == ("Nintendo", "")
    # The English article stands in, credited in English, its title without "(…)".
    assert found[3].text == "A magazine.\n\nSource: Wikipedia, CC BY-SA 4.0"
    assert found[3].title == "Nintendo Power"
    # In English, the English text.
    assert source.describe("Nintendo", "companies", "en")[0].text.startswith("A company.")
    # Series: no entry without an article, nothing confident.
    series = source.describe("Nintendo", "series", "de")
    assert [r.external_id for r in series] == ["Q11", "Q10", "Q15"]  # the name, then de
    assert not any(r.confident for r in series)


def test_company_name_variants(described: list[dict[str, Any]]) -> None:
    """A name Wikidata doesn't know is searched without its legal form and run together;
    series aren't."""
    source = WikipediaSource()
    for name in ("Nintendo Co., Ltd.", "Nin tendo!"):
        assert source.describe(name, "companies", "de")[0].external_id == "Q11", name
    searched = [c["search"] for c in described if c["action"] == "wbsearchentities"]
    assert searched == ["Nintendo Co., Ltd.", "Nintendo", "Nin tendo!", "Nin tendo", "Nintendo"]
    assert source.describe("Nintendo Co., Ltd.", "series", "de") == []


def test_description_in_every_language(described: list[dict[str, Any]]) -> None:
    source = WikipediaSource()
    record = source.description("Q11", "en")
    assert record is not None
    assert record.texts == {
        "de": "Ein Unternehmen.\n\nQuelle: Wikipedia, CC BY-SA 4.0",
        "en": "A company.\n\nSource: Wikipedia, CC BY-SA 4.0",
    }
    assert (record.text, record.language, record.title) == (record.texts["en"], "en", "Nintendo")
    assert record.company is None  # only asked for companies
    studio = source.description("Q14", "de", "companies")
    assert studio is not None
    assert (studio.texts, studio.text, studio.language) == ({}, "", "")
    assert source.description("Q12", "de") is None  # a game
    assert source.description("Q99", "de") is None  # missing
    assert source.description("bogus") is None


def test_company_description_api(
    api: Any, described: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.catalog.models import Company, Series

    nintendo = Company.objects.create(name="Nintendo")
    url = f"/catalog/companies/{nintendo.pk}/description/wikipedia"
    found = api.get(f"{url}/candidates").json()
    assert found[0] == {
        "external_id": "Q11",
        "title": "Nintendo",
        "label": "about Q11",
        "text": "Ein Unternehmen.\n\nQuelle: Wikipedia, CC BY-SA 4.0",
        "language": "de",
        "confident": True,
        "has_image": True,
    }
    assert described[0]["search"] == "Nintendo"
    api.get(f"{url}/candidates", {"q": " Big N "})
    assert any(c.get("search") == "Big N" for c in described)

    assert api.post(url, {"external_id": "Q11"}).json() == {
        "description": "Ein Unternehmen.\n\nQuelle: Wikipedia, CC BY-SA 4.0",
        "image": False,
    }
    nintendo.refresh_from_db()
    assert set(nintendo.descriptions) == {"de", "en"}  # both languages at once
    assert nintendo.external_ids == {"wikipedia": "Q11"}
    assert api.post(url, {"external_id": "Q12"}).status_code == 404  # a game

    # An entry with facts only keeps the texts; one in a single language replaces only
    # that one.
    api.post(url, {"external_id": "Q14"})
    nintendo.refresh_from_db()
    assert set(nintendo.descriptions) == {"de", "en"}
    assert nintendo.external_ids == {"wikipedia": "Q14"}
    api.post(url, {"external_id": "Q15"})
    nintendo.refresh_from_db()
    assert nintendo.descriptions["en"].startswith("A magazine.")
    assert nintendo.descriptions["de"].startswith("Ein Unternehmen.")

    zelda = Series.objects.create(name="Zelda")
    series_url = f"/catalog/series/{zelda.pk}/description/wikipedia"
    assert api.get(f"{series_url}/candidates").status_code == 200
    # Series have no facts: an entry without text has nothing to give.
    assert api.post(series_url, {"external_id": "Q14"}).status_code == 404
    taken = api.post(series_url, {"external_id": "Q10"}).json()
    assert taken["description"].startswith("Eine Konsole.")

    # Unknown sources, switched off, failing.
    assert api.get(f"/catalog/series/{zelda.pk}/description/igdb/candidates").status_code == 400
    monkeypatch.setattr("httpx.get", router({}))
    assert api.get(f"{series_url}/candidates").status_code == 502
    assert api.post(series_url, {"external_id": "Q11"}).status_code == 502
    save("wikipedia", enabled=False)
    assert api.post(series_url, {"external_id": "Q11"}).status_code == 400


def _commons(
    monkeypatch: pytest.MonkeyPatch, content: bytes, ctype: str = "image/svg+xml"
) -> list[str]:
    """Answers Wikidata/Wikipedia as `described` does, plus Commons with `content`."""
    fetched: list[str] = []
    inner = httpx.get

    def commons(url: str, *args: Any, **kwargs: Any) -> httpx.Response:
        assert kwargs["follow_redirects"] is False
        fetched.append(url)
        return response(content=content, ctype=ctype)

    def call(url: str, *args: Any, **kwargs: Any) -> httpx.Response:
        if host(url) == "upload.wikimedia.org":
            return commons(url, *args, **kwargs)
        return inner(url, *args, **kwargs)

    monkeypatch.setattr("httpx.get", call)
    return fetched


def test_company_logo(
    api: Any,
    described: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.catalog.models import Company

    nintendo = Company.objects.create(name="Nintendo")
    url = f"/catalog/companies/{nintendo.pk}/description/wikipedia"
    fetched = _commons(monkeypatch, SVG)
    assert api.post(url, {"external_id": "Q11", "image": True}).json()["image"] is True
    assert fetched == [NINTENDO_LOGO]
    nintendo.refresh_from_db()
    assert str(nintendo.image.name).endswith(".svg")
    assert nintendo.image.read() == SVG

    # An entry without a logo leaves the picture alone.
    assert api.post(url, {"external_id": "Q10", "image": True}).json()["image"] is False
    nintendo.refresh_from_db()
    assert nintendo.image


@pytest.mark.parametrize(
    ("content", "ctype"),
    [
        (
            b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
            "image/svg+xml",
        ),
        (b"<html></html>", "text/html"),
        (b"x" * (2 * 1024 * 1024 + 1), "image/png"),
    ],
)
def test_unusable_logo_keeps_text(
    api: Any,
    described: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    content: bytes,
    ctype: str,
) -> None:
    from apps.catalog.models import Company

    nintendo = Company.objects.create(name="Nintendo")
    _commons(monkeypatch, content, ctype)
    url = f"/catalog/companies/{nintendo.pk}/description/wikipedia"
    assert api.post(url, {"external_id": "Q11", "image": True}).json()["image"] is False
    nintendo.refresh_from_db()
    assert nintendo.descriptions["de"].startswith("Ein Unternehmen.")
    assert not nintendo.image


def test_logo_only_from_commons(db: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("httpx.get", router({}))
    source = WikipediaSource()
    for bad in (
        "https://evil.example/wikipedia/commons/a/ab/x.svg",
        "http://upload.wikimedia.org/wikipedia/commons/a/ab/x.svg",
        "https://upload.wikimedia.org/wikipedia/en/a/ab/x.svg",
    ):
        with pytest.raises(ProviderError):
            source.image(bad)
    with pytest.raises(ProviderError):  # network error
        source.image(NINTENDO_LOGO)


def test_company_facts(db: None, described: list[dict[str, Any]]) -> None:
    facts = WikipediaSource().description("Q11", "de", "companies").company  # type: ignore[union-attr]
    assert facts is not None
    assert (facts.founded, facts.dissolved, facts.country) == (1889, None, "JP")
    assert facts.headquarters == "Kyōto"
    assert facts.website == "https://www.nintendo.co.jp"
    assert facts.parent is not None
    assert facts.parent.names == ("Nintendo Holdings",)
    assert [r.external_id for r in facts.subsidiaries] == ["Q91", "Q92"]
    # Search results don't ask for facts.
    assert WikipediaSource().describe("Nintendo", "companies", "de")[0].company is None
    # An entry that knows none of it.
    console = WikipediaSource().description("Q10", "de", "companies")
    assert console is not None
    assert console.company is not None
    assert console.company.country == ""
    assert console.company.subsidiaries == ()


def test_company_takes_facts(api: Any, described: list[dict[str, Any]]) -> None:
    from apps.catalog.models import Company

    nintendo = Company.objects.create(name="Nintendo", headquarters="Old", country="US")
    holdings = Company.objects.create(name="nintendo holdings")
    monolith = Company.objects.create(name="Other name", external_ids={"wikipedia": "Q91"})
    retro = Company.objects.create(name="Retro Studios", parent=holdings)
    url = f"/catalog/companies/{nintendo.pk}/description/wikipedia"
    api.post(url, {"external_id": "Q11"})
    nintendo.refresh_from_db()
    monolith.refresh_from_db()
    retro.refresh_from_db()
    assert (nintendo.founded, nintendo.country, nintendo.headquarters) == (1889, "JP", "Kyōto")
    assert nintendo.website == "https://www.nintendo.co.jp"
    assert nintendo.parent == holdings  # found by name, any case
    assert monolith.parent == nintendo  # found by the remembered id
    assert retro.parent == holdings  # had a parent already
    detail = api.get(f"/catalog/companies/{nintendo.pk}").json()["company"]
    assert detail["parent"] == {"id": str(holdings.pk), "name": "nintendo holdings"}
    assert [s["name"] for s in detail["subsidiaries"]] == ["Other name"]

    # A parent that would make a loop is left out; unknown facts keep what we have.
    holdings.parent = monolith
    holdings.save()
    nintendo.parent = None
    nintendo.save()
    api.post(url, {"external_id": "Q11"})
    nintendo.refresh_from_db()
    assert nintendo.parent is None


def test_what_counts_as_a_company() -> None:
    from apps.providers.sources.wikipedia import _Hit, _is_kind

    def entity(**claims: list[str]) -> dict[str, Any]:
        return {"claims": {p: [_logo({"id": q}) for q in ids] for p, ids in claims.items()}}

    assert _is_kind(entity(P31=["Q210167"]), "companies")  # video game developer
    assert _is_kind(entity(P31=["Q43229"], P452=["Q112165968"]), "companies")  # org + industry
    assert not _is_kind(entity(P31=["Q43229"]), "companies")  # a bare organization
    assert _is_kind(entity(P452=["Q941594"]), "companies")  # video game industry
    assert _is_kind({"claims": {"P9650": [_logo("nintendo")]}}, "companies")  # IGDB id
    assert _is_kind(entity(P31=["Q7058673"]), "series")
    assert not _is_kind(entity(P31=["Q210167"]), "series")

    # The name itself counts more than an alias.
    label = _Hit("Q1", "CD Projekt RED", "", {"CD Projekt RED"})
    alias = _Hit("Q2", "cdp.pl", "", {"cdp.pl", "CD Projekt RED"})
    exact = WikipediaSource._exact
    assert (exact(label, {}, "CD Projekt Red"), exact(alias, {}, "CD Projekt Red")) == (2, 1)
    assert exact(alias, {}, "GOG") == 0


# --- IGDB's companies and choosing a picture ----------------------------------------------
def _png() -> bytes:
    from io import BytesIO

    from PIL import Image

    out = BytesIO()
    Image.new("RGB", (2, 2)).save(out, "PNG")
    return out.getvalue()


PNG = _png()
IGDB_NINTENDO = {
    "id": 70,
    "name": "Nintendo",
    "description": "From Kyoto.",
    "country": 392,
    "start_date": -2533161600,  # 1889-09-23
    "logo": {"image_id": "nlogo"},
    "parent": {"id": 1, "name": "Nintendo Holdings"},
    "websites": [
        {"url": "https://x.example/nintendo", "type": 5},
        {"url": "https://www.nintendo.co.jp", "type": 1},
    ],
}
IGDB_SPD = {"id": 2935, "name": "Nintendo SPD", "country": 999}
IGDB_LOGO = "https://images.igdb.com/igdb/image/upload/t_logo_med/nlogo.png"


@pytest.fixture
def igdb_companies(db: None, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """IGDB knows Nintendo and Nintendo SPD; images.igdb.com answers with a PNG."""
    save("igdb", enabled=True, secrets={"client_id": "id", "client_secret": "secret"})
    cache.clear()
    bodies: list[str] = []

    def companies(url: str, content: str = "", **kwargs: Any) -> httpx.Response:
        assert url.endswith("/companies")
        bodies.append(content)
        if "where id = 70;" in content or 'name ~ "Nintendo";' in content:
            return response(json=[IGDB_NINTENDO])
        if 'name ~ *"Nintendo"*' in content:
            return response(json=[IGDB_SPD, IGDB_NINTENDO])
        return response(json=[])

    monkeypatch.setattr(
        "httpx.post",
        router(
            {
                "https://id.twitch.tv": lambda *a, **k: response(json={"access_token": "t"}),
                "https://api.igdb.com": companies,
            }
        ),
    )
    inner = httpx.get

    def get(url: str, *args: Any, **kwargs: Any) -> httpx.Response:
        if host(url) == "images.igdb.com":
            assert kwargs["follow_redirects"] is False
            return response(content=PNG, ctype="image/png")
        return inner(url, *args, **kwargs)

    monkeypatch.setattr("httpx.get", get)
    return bodies


def test_igdb_describes_companies(igdb_companies: list[str]) -> None:
    source = IGDBSource()
    found = source.describe("Nintendo", "companies", "de")
    assert [(r.external_id, r.confident) for r in found] == [("70", True), ("2935", False)]
    assert "1889" in found[0].label
    assert found[0].language == "en"
    assert found[0].text == "From Kyoto.\n\nSource: IGDB"
    assert found[0].company is None
    assert found[0].images == ()
    assert found[1].text == ""
    assert found[1].language == ""
    # Another spelling: searched again without the legal form.
    assert source.describe("Nintendo Co., Ltd.", "companies")[0].external_id == "70"
    assert source.describe("Nintendo", "series") == []
    # Nothing at all: without "Studio" – offered, not sure.
    assert [
        (r.external_id, r.confident) for r in source.describe("Nintendo Studios", "companies")
    ] == [
        ("70", False),
        ("2935", False),
    ]
    assert source.describe("Games", "companies") == []

    record = source.description("70", "de", "companies")
    assert record is not None
    assert record.texts == {"en": "From Kyoto.\n\nSource: IGDB"}
    assert [i.url for i in record.images] == [IGDB_LOGO]
    assert record.company == CompanyFacts(
        founded=1889,
        country="JP",
        website="https://www.nintendo.co.jp",
        parent=EntryRef("1", ("Nintendo Holdings",)),
    )
    assert source.description("71", "de", "companies") is None  # unknown
    assert source.description("70", "de", "series") is None
    assert source.description("Q11") is None
    assert IGDBSource._country(None) == ""
    assert IGDBSource._country(999) == ""
    assert source.image(IGDB_LOGO) == PNG


@pytest.mark.parametrize(
    "answer",
    [
        lambda *a, **k: response(500, json={}),
        lambda *a, **k: response(content=b"<html>", ctype="text/html"),
    ],
)
def test_igdb_unusable_images(
    db: None, monkeypatch: pytest.MonkeyPatch, answer: Callable[..., httpx.Response]
) -> None:
    monkeypatch.setattr("httpx.get", router({"https://images.igdb.com": answer}))
    with pytest.raises(ProviderError):
        IGDBSource().image(IGDB_LOGO)
    with pytest.raises(ProviderError):
        IGDBSource().image("https://example.com/logo.png")


def test_company_description_from_igdb(api: Any, igdb_companies: list[str]) -> None:
    from apps.catalog.models import Company

    nintendo = Company.objects.create(name="Nintendo", descriptions={"de": "Aus Kyōto."})
    holdings = Company.objects.create(name="Nintendo Holdings")
    url = f"/catalog/companies/{nintendo.pk}/description/igdb"
    found = api.get(f"{url}/candidates").json()
    assert [c["external_id"] for c in found] == ["70", "2935"]
    assert found[0]["has_image"] is True
    assert api.post(url, {"external_id": "70", "image": True}).json()["image"] is True
    nintendo.refresh_from_db()
    assert nintendo.descriptions == {"de": "Aus Kyōto.", "en": "From Kyoto.\n\nSource: IGDB"}
    assert nintendo.external_ids == {"igdb": "70"}
    assert (nintendo.founded, nintendo.country, nintendo.parent) == (1889, "JP", holdings)
    assert str(nintendo.image.name).endswith(".png")


def test_logos_with_their_years() -> None:
    from apps.providers.sources.wikipedia import _logos

    def claim(name: str, rank: str = "normal", **years: int) -> dict[str, Any]:
        qualifiers = {
            p: [{"datavalue": {"value": {"time": f"+{y}-00-00T00:00:00Z"}}}]
            for p, y in years.items()
        }
        return {**_logo(name, rank), "qualifiers": qualifiers}

    entity = {
        "claims": {
            "P154": [
                claim("Red logo.svg", P580=1975, P582=2006),
                claim("Logo.svg", "preferred", P580=2016),
                claim("Gone.svg", "deprecated"),
                _logo({"not": "a file"}),
            ],
            "P2910": [claim("Logo.svg"), claim("Icon.png")],
        }
    }
    assert [(o.url.rsplit("/", 1)[1], o.label) for o in _logos(entity)] == [
        ("Logo.svg", "Logo (2016–)"),
        ("Red_logo.svg", "Red logo (1975–2006)"),
        ("Icon.png", "Icon"),
    ]


def test_choosing_a_picture(
    api: Any,
    described: list[dict[str, Any]],
    igdb_companies: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.catalog.models import Company, Series

    nintendo = Company.objects.create(
        name="Nintendo", external_ids={"wikipedia": "Q11", "igdb": "70", "other": "1"}
    )
    fetched = _commons(monkeypatch, SVG)
    url = f"/catalog/companies/{nintendo.pk}/images"
    found = api.get(url).json()
    assert [(c["source"], c["label"]) for c in found] == [
        ("igdb", "Logo"),
        ("wikipedia", "Nintendo"),
        ("wikipedia", "Nintendo 1970s"),
    ]
    preview = api.get("/catalog/term-image-preview", {"token": found[1]["token"]})
    assert preview.content == SVG
    assert preview["Content-Type"] == "image/svg+xml"
    assert "sandbox" in preview["Content-Security-Policy"]
    assert fetched == [NINTENDO_LOGO]

    detail = api.post(url, {"token": found[0]["token"]}).json()
    assert detail["image_url"].endswith(".png")
    nintendo.refresh_from_db()
    assert nintendo.image.read() == PNG

    # Tokens are opaque and checked; a source that doesn't answer is left out.
    for token in ("bogus", found[0]["token"][:-4]):
        assert api.post(url, {"token": token}).status_code == 400
    assert api.get(f"/catalog/series/{Series.objects.create(name='Zelda').pk}/images").json() == []
    monkeypatch.setattr(
        "httpx.post", router({"https://api.igdb.com": lambda *a, **k: response(500, json={})})
    )
    cache.set("providers:igdb:token:id", "t")
    assert [c["source"] for c in api.get(url).json()] == ["wikipedia", "wikipedia"]


def test_unusable_picture(
    api: Any, described: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.catalog.models import Company
    from apps.providers.services.integrations import encrypt

    nintendo = Company.objects.create(name="Nintendo", external_ids={"wikipedia": "Q11"})
    _commons(monkeypatch, b"<html></html>", "text/html")
    token = api.get(f"/catalog/companies/{nintendo.pk}/images").json()[0]["token"]
    assert api.get("/catalog/term-image-preview", {"token": token}).status_code == 502
    _commons(monkeypatch, b'<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>')
    assert api.get("/catalog/term-image-preview", {"token": token}).status_code == 400
    # Only the source's own hosts.
    foreign = encrypt('{"source": "wikipedia", "url": "https://example.com/x.svg"}')
    assert api.get("/catalog/term-image-preview", {"token": foreign}).status_code == 502
