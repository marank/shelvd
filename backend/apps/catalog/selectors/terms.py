"""Suggestions while picking a term or typing an edition: names that start with the query
first, then those containing it; ties by how often they're used."""

from __future__ import annotations

from collections import Counter
from typing import Literal, TypedDict, cast

from django.conf import settings
from django.db.models import Case, Count, IntegerField, Q, QuerySet, Value, When
from django.db.models.expressions import Combinable
from django.utils.translation import get_language

from ..models import Company, Franchise, Genre, Platform, Release, Series, Work

TermKind = Literal["companies", "genres", "series", "franchises"]
Term = Company | Genre | Series | Franchise
MODELS: dict[TermKind, type[Term]] = {
    "companies": Company,
    "genres": Genre,
    "series": Series,
    "franchises": Franchise,
}


class Edition(TypedDict):
    name: str
    uses: int


def _uses(kind: TermKind) -> Combinable:
    """What "uses" counts: games for genres and series; for a company the games it
    developed (or worked on a release of) plus the releases it published."""
    if kind == "companies":
        return (
            Count("developed", distinct=True)
            + Count("developed_releases", distinct=True)
            + Count("published", distinct=True)
        )
    return Count("works", distinct=True)


def _rank(field: str, query: str) -> Case:
    """0 for names starting with the query, else 1."""
    if not query:
        return Case(default=Value(0), output_field=IntegerField())
    return Case(
        When(**{f"{field}__istartswith": query}, then=Value(0)),
        default=Value(1),
        output_field=IntegerField(),
    )


def search_terms(kind: TermKind, query: str = "", limit: int = 20) -> QuerySet[Term]:
    query = query.strip()
    qs = MODELS[kind].objects.all()
    if query:
        qs = qs.filter(name__icontains=query)
    qs = qs.annotate(uses=_uses(kind), rank=_rank("name", query))
    return qs.order_by("rank", "-uses", "name")[:limit]


def editions(query: str = "", limit: int = 20) -> list[Edition]:
    query = query.strip()
    qs = Release.objects.exclude(edition="")
    if query:
        qs = qs.filter(edition__icontains=query)
    rows = (
        qs.order_by()
        .values("edition")
        .annotate(uses=Count("id"), rank=_rank("edition", query))
        .order_by("rank", "-uses", "edition")[:limit]
    )
    return [{"name": row["edition"], "uses": row["uses"]} for row in rows]


class TermWork(TypedDict):
    id: object
    title: str
    year: int | None
    cover_url: str | None
    cover_aspect: float | None
    manufacturer: str
    platforms: list[Platform]


class RelatedTerm(TypedDict):
    kind: TermKind
    id: object
    name: str
    count: int


class TermRefOut(TypedDict):
    id: object
    name: str


class CompanyDetails(TypedDict):
    founded: int | None
    dissolved: int | None
    country: str
    headquarters: str
    website: str
    parent: TermRefOut | None
    subsidiaries: list[TermRefOut]


def company_details(company: Company) -> CompanyDetails:
    parent = company.parent
    return {
        "founded": company.founded,
        "dissolved": company.dissolved,
        "country": company.country,
        "headquarters": company.headquarters,
        "website": company.website,
        "parent": {"id": parent.pk, "name": parent.name} if parent else None,
        "subsidiaries": [
            {"id": c.pk, "name": c.name} for c in company.subsidiaries.order_by("name")
        ],
    }


def description_for(texts: dict[str, str], language: str | None = None) -> tuple[str, str]:
    """(text, its language): the reader's language, else the site's, else any other."""
    wanted = (language or get_language() or settings.LANGUAGE_CODE).split("-")[0]
    order = [wanted, settings.LANGUAGE_CODE, *(code for code, _name in settings.LANGUAGES)]
    for code in [*order, *texts]:
        if texts.get(code):
            return texts[code], code
    return "", ""


class TermDetail(TypedDict):
    id: object
    name: str
    description: str
    description_language: str
    descriptions: dict[str, str]
    image_url: str | None
    image_tone: str
    works: list[TermWork]
    published: list[TermWork]
    related: list[RelatedTerm]
    company: CompanyDetails | None
    franchise: TermRefOut | None
    parts: list[TermRefOut]


def _games(works: QuerySet[Work]) -> list[Work]:
    return list(
        works.distinct()
        .prefetch_related("releases__platform", "genres", "series", "franchises", "developers")
        .order_by("first_release_date", "title")
    )


def _work(work: Work) -> TermWork:
    releases = sorted(work.releases.all(), key=lambda r: (r.sort_date, r.pk))
    covered = next((r for r in releases if r.cover), None)
    years = [r.year for r in releases if r.year]
    platforms = {r.platform.pk: r.platform for r in releases}
    return {
        "id": work.pk,
        "title": work.title,
        "year": work.first_release_date.year
        if work.first_release_date
        else min(years, default=None),
        "cover_url": work.shown_cover()[0],
        "cover_aspect": work.shown_cover()[1],
        "manufacturer": (covered or releases[0]).platform.manufacturer if releases else "",
        "platforms": sorted(platforms.values(), key=lambda p: (p.release_year or 0, p.name)),
    }


def _related(term: Term | Platform, works: list[Work], limit: int = 12) -> list[RelatedTerm]:
    """The genres, series and developers these games have most often (besides `term`)."""
    counts: Counter[tuple[TermKind, object]] = Counter()
    names: dict[tuple[TermKind, object], str] = {}
    for work in works:
        for kind, terms in (
            ("genres", work.genres.all()),
            ("series", work.series.all()),
            ("franchises", work.franchises.all()),
            ("companies", work.developers.all()),
        ):
            for other in terms:
                if type(other) is type(term) and other.pk == term.pk:
                    continue
                key = (cast(TermKind, kind), other.pk)
                counts[key] += 1
                names[key] = other.name
    top = sorted(counts.items(), key=lambda entry: (-entry[1], names[entry[0]].lower()))
    return [
        {"kind": kind, "id": pk, "name": names[(kind, pk)], "count": count}
        for (kind, pk), count in top[:limit]
    ]


def term_detail(term: Term) -> TermDetail:
    """A term with its games, oldest first: a company's developed ones in `works` and
    those it published (a release of) in `published`; genres and series only have
    `works`. `related`: what these games have in common besides it."""
    published: list[Work] = []
    if isinstance(term, Company):
        # The games it developed, or worked on one release of.
        works = _games(Work.objects.filter(Q(developers=term) | Q(releases__developers=term)))
        published = _games(Work.objects.filter(releases__publisher=term))
    elif isinstance(term, Genre):
        works = _games(Work.objects.filter(genres=term))
    elif isinstance(term, Franchise):
        works = _games(Work.objects.filter(franchises=term))
    else:
        works = _games(Work.objects.filter(series=term))
    every = list({w.pk: w for w in [*works, *published]}.values())
    description, language = description_for(term.descriptions)
    return {
        "id": term.pk,
        "name": term.name,
        "description": description,
        "description_language": language,
        "descriptions": term.descriptions,
        "image_url": term.image.url if term.image else None,
        "image_tone": term.image_tone,
        "works": [_work(w) for w in works],
        "published": [_work(w) for w in published],
        "related": _related(term, every),
        "company": company_details(term) if isinstance(term, Company) else None,
        "franchise": (
            {"id": term.franchise.pk, "name": term.franchise.name}
            if isinstance(term, Series) and term.franchise
            else None
        ),
        "parts": (
            [{"id": s.pk, "name": s.name} for s in term.series.order_by("name")]
            if isinstance(term, Franchise)
            else []
        ),
    }


class PlatformGames(TypedDict):
    works: list[TermWork]
    related: list[RelatedTerm]


def platform_games(platform: Platform) -> PlatformGames:
    """The catalog's games with a release on the platform, oldest first, and what they
    have in common (genres, series, developers)."""
    works = _games(Work.objects.filter(releases__platform=platform))
    return {"works": [_work(w) for w in works], "related": _related(platform, works)}
