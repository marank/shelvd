"""Wikipedia via Wikidata: titles, descriptions and first release dates in the reader's
language (German, English …), where IGDB only has English texts – and descriptions and
logos of companies and series, plus a company's facts (founded, country, seat, website,
parent and subsidiaries – Wikidata's data is CC0).

Wikidata finds the game (an item that is a video game, with an article in that
language's Wikipedia); the article's introduction becomes the description. Texts are
CC BY-SA 4.0: a source line is appended to every description we take. Logos (P154) are
files on Wikimedia Commons, fetched from upload.wikimedia.org only. No key needed;
Wikimedia asks for a User-Agent that says who we are.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any, NamedTuple
from urllib.parse import quote, urlsplit

import httpx
from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _

from ..services.integrations import Config, config
from .base import (
    CompanyFacts,
    DescriptionRecord,
    EntryRef,
    GameRecord,
    GetFromAll,
    ImageOption,
    PlatformFacts,
    ProviderError,
)
from .names import DISAMBIGUATION, normalize, variants

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIPEDIA_API = "https://{language}.wikipedia.org/w/api.php"
COMMONS_FILES = "https://upload.wikimedia.org/wikipedia/commons/"
IMAGE_TYPES = {"image/svg+xml", "image/png", "image/jpeg", "image/webp"}
IMAGE_MAX_BYTES = 25 * 1024 * 1024  # photos are shrunk to 2 MB before they're kept
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
PICTURE_TYPES = {"image/svg+xml", "image/png", "image/jpeg", "image/webp"}
USER_AGENT = "shelvd/1.0 (https://github.com/marank/shelvd; game collection manager)"
# Instance of (P31) one of these, or an IGDB id (P5794), makes an item a game: video
# game, free video game, Pokémon paired versions ("Pokémon Karmesin und Purpur" has the
# article, its single games don't).
GAME_CLASSES = {"Q7889", "Q21125433", "Q116774927"}
# What companies and series usually are; these come first among the candidates.
TERM_CLASSES = {
    "companies": {
        "Q210167",  # video game developer
        "Q1137109",  # video game publisher
        "Q4830453",  # business
        "Q783794",  # company
        "Q891723",  # public company
        "Q6881511",  # enterprise
    },
    "series": {
        "Q7058673",  # video game series
        "Q196600",  # media franchise
        "Q141546978",  # video game franchise
        "Q1667921",  # novel series (some franchises are filed so)
    },
    "franchises": {
        "Q196600",  # media franchise
        "Q141546978",  # video game franchise
        "Q7058673",  # video game series (many brands are only filed so)
        "Q1667921",  # novel series
    },
}
# What each kind is first of all: on a tie the series beats the franchise of the same
# name for a series ("Mario"), the franchise the series for a franchise.
PRIMARY_CLASSES = {"series": {"Q7058673"}, "franchises": {"Q196600", "Q141546978"}}
# What points to a series or franchise: games are "part of the series" (P179), series and
# games belong to a "media franchise" (P8345). A name Wikidata files differently ("Advance
# Wars" is in "Wars") is found through them.
POINTS_TO = {"series": "P179", "franchises": "P8345"}
# How Wikipedia tells such articles apart from a person or a word of the same name:
# "Anno (Computerspielreihe)", "Anno (video game series)".
TITLE_SUFFIXES = {
    "series": {
        "de": ("Computerspielreihe", "Computerspielserie", "Spieleserie", "Videospielreihe"),
        "en": ("video game series", "series", "franchise"),
    },
    "franchises": {
        "de": ("Franchise", "Medien-Franchise", "Computerspielreihe", "Computerspielserie"),
        "en": ("franchise", "media franchise", "video game series"),
    },
}
# The two the UI speaks; the other one's article stands in when the reader's has none.
LANGUAGES = {"de", "en"}
ANY_LANGUAGE = "mul"  # Wikidata's label for every language
SITES = "dewiki|enwiki"
# Games companies that are filed under another class: a subsidiary, privately held
# company, division, software company, corporation – or anything in the video game
# industry (P452) or with an IGDB company id (P9650), or an organization with any
# industry (Shiro Games: "computer programming"; schools and bands have none).
COMPANY_CLASSES = TERM_CLASSES["companies"] | {
    "Q658255",
    "Q1589009",
    "Q166280",
    "Q1058914",
    "Q167037",
}
VIDEO_GAME_INDUSTRY = "Q941594"
ORGANIZATION = "Q43229"
IGDB_COMPANY = "P9650"
# Logo, icon, small logo image – and for platforms photos of the device.
LOGO_PROPERTIES = (("P154", "logo"), ("P2910", "icon"), ("P8972", "icon"))
PHOTO = ("P18", "photo")
# Consoles, handhelds, computers (Wikidata files many as "product model" only; those are
# known by their IGDB platform id).
PLATFORM_CLASSES = {
    "Q8076",  # video game console
    "Q941818",  # handheld game console
    "Q56682555",  # video game console model
    "Q115187350",  # home video game console model
    "Q241317",  # computing platform
}
IGDB_PLATFORM = "P5795"


def _claim_ids(entity: dict[str, Any], prop: str) -> set[str]:
    ids = set()
    for claim in entity.get("claims", {}).get(prop, []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, dict) and "id" in value:
            ids.add(str(value["id"]))
    return ids


def _first_release(entity: dict[str, Any]) -> date | None:
    """The earliest publication date (P577) given to the day."""
    dates = []
    for claim in entity.get("claims", {}).get("P577", []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if not isinstance(value, dict) or value.get("precision") != 11:
            continue
        try:
            dates.append(date.fromisoformat(str(value["time"])[1:11]))
        except KeyError, ValueError:
            continue
    return min(dates) if dates else None


def _values(entity: dict[str, Any], prop: str) -> list[Any]:
    """A property's values, preferred ones first, deprecated ones left out."""
    claims = [
        c
        for c in entity.get("claims", {}).get(prop, [])
        if c.get("rank") != "deprecated"
        and c.get("mainsnak", {}).get("datavalue", {}).get("value") is not None
    ]
    claims.sort(key=lambda c: c.get("rank") != "preferred")
    return [c["mainsnak"]["datavalue"]["value"] for c in claims]


def _ids(entity: dict[str, Any], prop: str) -> list[str]:
    return [str(v["id"]) for v in _values(entity, prop) if isinstance(v, dict) and "id" in v]


def _years(entity: dict[str, Any], prop: str) -> list[int]:
    """Years of a time property (given at least to the year)."""
    years = []
    for value in _values(entity, prop):
        if isinstance(value, dict) and value.get("precision", 0) >= 9:
            match = re.match(r"\+(\d{4})-", str(value.get("time", "")))
            if match:
                years.append(int(match.group(1)))
    return years


def _commons_url(name: str) -> str:
    """A Commons file's URL (md5 of the name picks its folder)."""
    name = name.replace(" ", "_")
    digest = hashlib.md5(name.encode(), usedforsecurity=False).hexdigest()
    return f"{COMMONS_FILES}{digest[0]}/{digest[:2]}/{quote(name)}"


def _qualifier_year(claim: dict[str, Any], prop: str) -> int | None:
    for snak in claim.get("qualifiers", {}).get(prop, []):
        value = snak.get("datavalue", {}).get("value", {})
        match = re.match(r"\+(\d{4})-", str(value.get("time", "")))
        if match:
            return int(match.group(1))
    return None


def _logos(entity: dict[str, Any], photos: bool = False) -> tuple[ImageOption, ...]:
    """Every logo (P154), then icon (P2910) and small logo (P8972) on Commons – with
    `photos` also pictures of the thing (P18): the current one first, each named by its
    file and the years it was used ("1975–2006")."""
    found: dict[str, ImageOption] = {}
    for prop, kind in (*LOGO_PROPERTIES, *((PHOTO,) if photos else ())):
        claims = [
            c
            for c in entity.get("claims", {}).get(prop, [])
            if c.get("rank") != "deprecated"
            and isinstance(c.get("mainsnak", {}).get("datavalue", {}).get("value"), str)
        ]
        claims.sort(key=lambda c: c.get("rank") != "preferred")
        for claim in claims:
            name = str(claim["mainsnak"]["datavalue"]["value"])
            start, end = _qualifier_year(claim, "P580"), _qualifier_year(claim, "P582")
            years = f"{start or ''}–{end or ''}" if start or end else ""
            label = name.rsplit(".", 1)[0]
            label = f"{label} ({years})" if years else label
            found.setdefault(name, ImageOption(_commons_url(name), label, kind))
    return tuple(found.values())


def _logo_url(entity: dict[str, Any]) -> str:
    """The current logo's URL on Commons."""
    logos = _logos(entity)
    return logos[0].url if logos else ""


def _is_kind(entity: dict[str, Any], kind: str) -> bool:
    """Whether the entry is the kind of thing asked for (a company, series, platform)."""
    classes = _claim_ids(entity, "P31")
    if kind == "companies":
        industries = _claim_ids(entity, "P452")
        return bool(
            classes & COMPANY_CLASSES
            or VIDEO_GAME_INDUSTRY in industries
            or (ORGANIZATION in classes and industries)
            or IGDB_COMPANY in entity.get("claims", {})
        )
    if kind == "platforms":
        return bool(classes & PLATFORM_CLASSES or IGDB_PLATFORM in entity.get("claims", {}))
    return bool(classes & TERM_CLASSES.get(kind, set()))


def _articles(entity: dict[str, Any]) -> dict[str, str]:
    """Article titles by language."""
    sitelinks = entity.get("sitelinks", {})
    return {
        lang: str(sitelinks[f"{lang}wiki"]["title"])
        for lang in sorted(LANGUAGES)
        if sitelinks.get(f"{lang}wiki", {}).get("title")
    }


def _pick[T](by_language: Mapping[str, T], lang: str) -> tuple[str, T | None]:
    """The asked language's, else another's: (language, value)."""
    for code in [lang, *sorted(by_language)]:
        if code in by_language:
            return code, by_language[code]
    return "", None


@dataclass
class _Hit:
    """A search result: id, label, short description and the names it matched by."""

    qid: str
    label: str
    description: str
    names: set[str]


class _Candidate(NamedTuple):
    """A hit worth offering, with its entity, articles, whether it is of the wanted kind
    and how exactly its name matches (WikipediaSource._exact)."""

    hit: _Hit
    entity: dict[str, Any]
    articles: dict[str, str]
    typed: bool
    exact: int


class WikipediaSource(GetFromAll):
    name = "wikipedia"
    catalog = False
    fields = frozenset({"title", "summary", "first_release_date"})

    def __init__(self, cfg: Config | None = None) -> None:
        self.cfg = cfg or config("wikipedia")

    def enabled(self) -> bool:
        return self.cfg.active

    # --- HTTP -----------------------------------------------------------------------
    def _get(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        try:
            response = httpx.get(
                url,
                params={**params, "format": "json"},
                headers={"User-Agent": USER_AGENT},
                timeout=settings.PROVIDER_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"Wikipedia request failed: {exc}") from exc
        if not isinstance(data, dict) or "error" in data:
            raise ProviderError("Wikipedia returned an unexpected response.")
        return data

    def test(self) -> str:
        self._get(WIKIDATA_API, {"action": "wbsearchentities", "search": "Zelda", "language": "en"})
        return _("OK")

    # --- MetadataSource ---------------------------------------------------------------
    def search(
        self, query: str, platform_external_id: str | None = None, language: str = "en"
    ) -> list[GameRecord]:
        lang = self._language(language)
        return self._records([qid for qid, _ in self._search(query, lang)], lang)

    def get_all(
        self, external_id: str, platform_external_id: str | None = None, language: str = "en"
    ) -> list[GameRecord]:
        if not re.fullmatch(r"Q\d+", external_id):
            return []
        return self._records([external_id], self._language(language))

    # --- DescriptionSource ------------------------------------------------------------
    def describe(self, query: str, kind: str, language: str = "en") -> list[DescriptionRecord]:
        """Candidates, likeliest first: the right kind of thing, then exactly that name,
        then with an article in the language, then with any. A company's name that finds
        nothing fitting is searched again in other spellings."""
        lang = self._language(language)
        hits = self._find(query, lang)
        entities = self._entities([h.qid for h in hits], SITES, labels=True)

        def confident() -> bool:
            return self._confident(hits, entities, query, kind)

        if kind == "companies" and not confident():
            for variant in variants(query):
                hits += self._new_hits(self._find(variant, lang), hits, entities)
                if confident():
                    break
        if kind in POINTS_TO and not confident() and lang != "en":
            # Names that are first given names or places in German ("Mario", "Anno").
            hits += self._new_hits(self._find(query, "en"), hits, entities)
        if kind in TITLE_SUFFIXES and not confident():
            # The article for exactly that is the likeliest.
            hits = self._new_hits(self._titled(query, kind, lang), hits, entities) + hits
        if kind in POINTS_TO and not confident():
            hits += self._pointed_to(hits, entities, kind, lang)
        return self._candidates(hits, entities, query, kind, lang)

    def _confident(self, hits: list[_Hit], entities: dict[str, Any], query: str, kind: str) -> bool:
        """A fitting entry that will be offered (only companies may lack an article)."""
        return any(
            _is_kind(entity := entities.get(h.qid) or {}, kind)
            and self._exact(h, entities, query)
            and (kind == "companies" or bool(_articles(entity)))
            for h in hits
        )

    def _new_hits(
        self, found: list[_Hit], hits: list[_Hit], entities: dict[str, Any]
    ) -> list[_Hit]:
        """The hits in `found` that aren't among `hits` yet; `entities` gets theirs."""
        seen = {h.qid for h in hits}
        more = [h for h in found if h.qid not in seen]
        entities.update(self._entities([h.qid for h in more], SITES, labels=True))
        return more

    def _titled(self, query: str, kind: str, lang: str) -> list[_Hit]:
        """The entries of the articles "<query> (<what it is>)" in either language. Not
        through redirects: "New Super Mario Bros. (series)" only leads to "Super Mario"."""
        name = query.strip()
        found: list[_Hit] = []
        for code, suffixes in TITLE_SUFFIXES[kind].items():
            titles = [f"{name} ({suffix})" for suffix in suffixes]
            pages = (
                self._get(
                    WIKIPEDIA_API.format(language=code),
                    {
                        "action": "query",
                        "prop": "pageprops",
                        "ppprop": "wikibase_item",
                        "titles": "|".join(titles),
                        "formatversion": "2",
                    },
                )
                .get("query", {})
                .get("pages", [])
            )
            for page in pages:
                qid = str((page.get("pageprops") or {}).get("wikibase_item") or "")
                if qid and qid not in {h.qid for h in found}:
                    found.append(_Hit(qid, name, str(page.get("title", "")), {name}))
        return found

    def _pointed_to(
        self, hits: list[_Hit], entities: dict[str, Any], kind: str, lang: str
    ) -> list[_Hit]:
        """The series (franchises) the found games and series point to, as more hits;
        `entities` gets theirs."""
        seen = {h.qid for h in hits}
        targets: list[str] = []
        for hit in hits:
            for qid in _ids(entities.get(hit.qid) or {}, POINTS_TO[kind]):
                if qid not in seen and qid not in targets:
                    targets.append(qid)
        found = self._entities(targets[:20], SITES, labels=True)
        entities.update(found)
        more = []
        for qid in targets[:20]:
            labels = (found.get(qid) or {}).get("labels", {})
            names = {str(v["value"]) for v in labels.values()}
            _code, label = _pick({k: v["value"] for k, v in labels.items()}, lang)
            if names:
                more.append(_Hit(qid, str(label or qid), "", names))
        return more

    def description(
        self, external_id: str, language: str = "en", kind: str = ""
    ) -> DescriptionRecord | None:
        if not re.fullmatch(r"Q\d+", external_id):
            return None
        lang = self._language(language)
        entity = self._entities([external_id], SITES, labels=True).get(external_id) or {}
        if not entity.get("claims") and not entity.get("sitelinks"):
            return None  # missing
        if _claim_ids(entity, "P31") & GAME_CLASSES:
            return None
        articles = _articles(entity)
        texts = {}
        for code, title in articles.items():
            extract = self._extracts([title], code).get(title)
            if extract:
                with translation.override(code):
                    texts[code] = f"{extract}\n\n{_('Source: Wikipedia, CC BY-SA 4.0')}"
        text_language, text = _pick(texts, lang)
        labels = entity.get("labels", {})
        _code, label = _pick({k: v["value"] for k, v in labels.items()}, lang)
        return DescriptionRecord(
            source=self.name,
            external_id=external_id,
            title=DISAMBIGUATION.sub("", articles.get(text_language) or str(label or "")),
            text=text or "",
            language=text_language,
            texts=texts,
            image_url=_logo_url(entity),
            images=_logos(entity, photos=kind == "platforms"),
            company=self._company(entity, lang) if kind == "companies" else None,
            platform=self._platform(entity, lang) if kind == "platforms" else None,
            franchise=self._franchise(entity, lang) if kind == "series" else None,
        )

    def image(self, url: str) -> bytes:
        if not url.startswith(COMMONS_FILES) or urlsplit(url).hostname != "upload.wikimedia.org":
            raise ProviderError("Not a Wikimedia Commons file.")
        try:
            response = httpx.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=settings.PROVIDER_TIMEOUT,
                follow_redirects=False,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Wikimedia Commons request failed: {exc}") from exc
        content_type = response.headers.get("content-type", "").split(";")[0].strip()
        if content_type not in IMAGE_TYPES or len(response.content) > IMAGE_MAX_BYTES:
            raise ProviderError("Wikimedia Commons returned no usable image.")
        return response.content

    def search_images(self, query: str, limit: int = 24) -> list[ImageOption]:
        """Pictures on Wikimedia Commons for a query ("Nintendo DS icon"): SVGs as they
        are, others as a thumbnail at most 1600 px wide (photos are big)."""
        found = self._get(
            COMMONS_API,
            {
                "action": "query",
                "generator": "search",
                "gsrnamespace": "6",
                "gsrsearch": query,
                "gsrlimit": str(limit),
                "prop": "imageinfo",
                "iiprop": "url|mime",
                "iiurlwidth": "1600",
            },
        )
        pages = sorted(
            (found.get("query") or {}).get("pages", {}).values(),
            key=lambda page: page.get("index", 0),
        )
        options = []
        for page in pages:
            info = (page.get("imageinfo") or [{}])[0]
            mime = str(info.get("mime", ""))
            # Without the tracking parameters Commons adds ("?utm_source=…").
            url = str(info.get("url" if mime == "image/svg+xml" else "thumburl") or "")
            url = url.split("?", 1)[0]
            if mime not in PICTURE_TYPES or not url.startswith(COMMONS_FILES):
                continue
            label = str(page.get("title", "")).removeprefix("File:").rsplit(".", 1)[0]
            options.append(ImageOption(url, label, "logo" if mime == "image/svg+xml" else "photo"))
        return options

    # --- mapping ------------------------------------------------------------------------
    def _search(self, query: str, lang: str) -> list[tuple[str, str]]:
        """Wikidata items matching the query: (id, short description)."""
        found = self._get(
            WIKIDATA_API,
            {
                "action": "wbsearchentities",
                "search": query,
                "language": lang,
                "uselang": lang,
                "type": "item",
                "limit": "20",
            },
        ).get("search", [])
        return [(str(i["id"]), str(i.get("description", ""))) for i in found if i.get("id")]

    def _company(self, entity: dict[str, Any], lang: str) -> CompanyFacts:
        """Founded/dissolved years, country code, seat, website, parent and subsidiaries;
        names of the linked entries in one request, the country's code in another."""
        seat = _ids(entity, "P159")[:1]
        parent = _ids(entity, "P749")[:1]
        subsidiaries = _ids(entity, "P355")[:40]
        names = self._labels([*seat, *parent, *subsidiaries], lang)
        countries = _ids(entity, "P17")
        websites = [
            v for v in _values(entity, "P856") if isinstance(v, str) and v.startswith("http")
        ]
        founded, dissolved = _years(entity, "P571"), _years(entity, "P576")

        def ref(qid: str) -> EntryRef | None:
            return EntryRef(qid, names[qid]) if names.get(qid) else None

        return CompanyFacts(
            founded=min(founded) if founded else None,
            dissolved=max(dissolved) if dissolved else None,
            country=self._country_code(countries[0]) if countries else "",
            headquarters=names[seat[0]][0] if seat and names.get(seat[0]) else "",
            website=websites[0] if websites else "",
            parent=ref(parent[0]) if parent else None,
            subsidiaries=tuple(r for q in subsidiaries if (r := ref(q))),
        )

    def _franchise(self, entity: dict[str, Any], lang: str) -> EntryRef | None:
        """The media franchise (P8345) a series belongs to, with its names."""
        qid = next(iter(_ids(entity, "P8345")), None)
        names = self._labels([qid], lang) if qid else {}
        return EntryRef(qid, names[qid]) if qid and names.get(qid) else None

    def _platform(self, entity: dict[str, Any], lang: str) -> PlatformFacts:
        """Short name, release and discontinuation years, manufacturer, predecessors and
        successors (their names in one request)."""
        maker = _ids(entity, "P176")[:1]
        before, after = _ids(entity, "P155")[:10], _ids(entity, "P156")[:10]
        names = self._labels([*maker, *before, *after], lang)
        short = {
            str(v.get("language")): str(v.get("text"))
            for v in _values(entity, "P1813")
            if isinstance(v, dict) and v.get("text")
        }
        released, discontinued = _years(entity, "P577"), _years(entity, "P2669")

        def refs(ids: list[str]) -> tuple[EntryRef, ...]:
            return tuple(EntryRef(q, names[q]) for q in ids if names.get(q))

        return PlatformFacts(
            short_name=(_pick(short, lang)[1] or "")[:20],
            released=min(released) if released else None,
            discontinued=max(discontinued) if discontinued else None,
            manufacturer=next(iter(refs(maker)), None),
            predecessors=refs(before),
            successors=refs(after),
        )

    def _labels(self, ids: list[str], lang: str) -> dict[str, tuple[str, ...]]:
        """Each entry's names: in the language first, then English, then the label for
        every language ("mul" – newer entries such as the Switch 2 have only that)."""
        if not ids:
            return {}
        entities = self._get(
            WIKIDATA_API,
            {
                "action": "wbgetentities",
                "ids": "|".join(ids[:50]),
                "props": "labels",
                "languages": f"{lang}|en|{ANY_LANGUAGE}",
            },
        ).get("entities", {})
        labels: dict[str, tuple[str, ...]] = {}
        for qid in ids:
            found = (entities.get(qid) or {}).get("labels", {})
            names = [str(found[k]["value"]) for k in (lang, "en", ANY_LANGUAGE) if k in found]
            if names:
                labels[qid] = tuple(dict.fromkeys(names))
        return labels

    def _country_code(self, qid: str) -> str:
        """ISO 3166-1 alpha-2 (P297) of a country entry, "" if it has none."""
        claims = self._get(
            WIKIDATA_API, {"action": "wbgetclaims", "entity": qid, "property": "P297"}
        ).get("claims", {})
        codes = [v for v in _values({"claims": claims}, "P297") if isinstance(v, str)]
        return codes[0].upper() if codes and re.fullmatch(r"[A-Za-z]{2}", codes[0]) else ""

    def _entities(self, ids: list[str], sites: str, labels: bool = False) -> dict[str, Any]:
        if not ids:
            return {}
        params = {
            "action": "wbgetentities",
            "ids": "|".join(ids[:20]),
            "props": "claims|sitelinks|labels" if labels else "claims|sitelinks",
            "sitefilter": sites,
        }
        if labels:
            params["languages"] = "|".join(sorted({*LANGUAGES, ANY_LANGUAGE}))
        entities: dict[str, Any] = self._get(WIKIDATA_API, params).get("entities", {})
        return entities

    def _find(self, query: str, lang: str) -> list[_Hit]:
        found = self._get(
            WIKIDATA_API,
            {
                "action": "wbsearchentities",
                "search": query,
                "language": lang,
                "uselang": lang,
                "type": "item",
                "limit": "20",
            },
        ).get("search", [])
        return [
            _Hit(
                qid=str(item["id"]),
                label=str(item.get("label", "")),
                description=str(item.get("description", "")),
                names={
                    str(item.get("label", "")),
                    str(item.get("match", {}).get("text", "")),
                    *map(str, item.get("aliases", [])),
                },
            )
            for item in found
            if item.get("id")
        ]

    @staticmethod
    def _exact(hit: _Hit, entities: dict[str, Any], query: str) -> int:
        """2: the query is its name, 1: one of its other names (an alias – cdp.pl is also
        called "CD Projekt RED"), 0: neither."""
        labels = (entities.get(hit.qid) or {}).get("labels", {})
        own = {hit.label} | {str(v.get("value", "")) for v in labels.values()}
        wanted = normalize(query)
        if wanted in {normalize(n) for n in own if n}:
            return 2
        return 1 if wanted in {normalize(n) for n in hit.names if n} else 0

    def _candidates(
        self,
        hits: list[_Hit],
        entities: dict[str, Any],
        query: str,
        kind: str,
        lang: str,
    ) -> list[DescriptionRecord]:
        """Records for the hits, games left out; without an article only companies (they
        still have facts). Texts in the language, else the other's."""
        items = self._candidate_items(hits, entities, query, kind)
        wanted: dict[str, list[str]] = {}
        for item in items:
            code, title = _pick(item.articles, lang)
            if title:
                wanted.setdefault(code, []).append(title)
        extracts = {code: self._extracts(titles, code) for code, titles in wanted.items()}
        records = [
            record
            for item in items
            if (record := self._candidate(item, extracts, kind, lang)) is not None
        ]
        # Stable: the search's order within each group.
        return [record for _key, record in sorted(records, key=lambda r: r[0])]

    def _candidate_items(
        self, hits: list[_Hit], entities: dict[str, Any], query: str, kind: str
    ) -> list[_Candidate]:
        """The hits worth offering: no games; without an article only companies."""
        items: list[_Candidate] = []
        for hit in hits:
            entity = entities.get(hit.qid) or {}
            if _claim_ids(entity, "P31") & GAME_CLASSES:
                continue
            articles = _articles(entity)
            typed = _is_kind(entity, kind)
            if articles or (kind == "companies" and typed):
                exact = self._exact(hit, entities, query)
                items.append(_Candidate(hit, entity, articles, typed, exact))
        return items

    def _candidate(
        self, item: _Candidate, extracts: dict[str, dict[str, str]], kind: str, lang: str
    ) -> tuple[tuple[bool, int, bool, bool, bool], DescriptionRecord] | None:
        """The record of one candidate with its sort key; None for an empty article about
        something else."""
        hit, entity, articles, typed, exact = item
        code, title = _pick(articles, lang)
        extract = extracts.get(code, {}).get(title or "", "")
        if title and not extract and not typed:
            return None
        with translation.override(code or lang):
            source = _("Source: Wikipedia, CC BY-SA 4.0")
        labels = entity.get("labels", {})
        _code, label = _pick({k: v["value"] for k, v in labels.items()}, lang)
        key = (
            not typed,
            -exact,
            not PRIMARY_CLASSES.get(kind, set()) & _claim_ids(entity, "P31"),
            lang not in articles,
            not articles,
        )
        return key, DescriptionRecord(
            source=self.name,
            external_id=hit.qid,
            title=DISAMBIGUATION.sub("", title or str(label or hit.label or hit.qid)),
            label=hit.description,
            text=f"{extract}\n\n{source}" if extract else "",
            language=code if extract else "",
            image_url=_logo_url(entity),
            confident=typed and exact > 0,
        )

    @staticmethod
    def _language(language: str) -> str:
        lang = language.split("-")[0].lower()
        return lang if lang in LANGUAGES else "en"

    def _records(self, ids: list[str], lang: str) -> list[GameRecord]:
        if not ids:
            return []
        site = f"{lang}wiki"
        entities = self._entities(ids, site)
        games: list[tuple[str, dict[str, Any], str]] = []
        for qid in ids:
            entity = entities.get(qid) or {}
            article = entity.get("sitelinks", {}).get(site, {}).get("title")
            is_game = _claim_ids(entity, "P31") & GAME_CLASSES or "P5794" in entity.get(
                "claims", {}
            )
            if article and is_game:
                games.append((qid, entity, str(article)))
        extracts = self._extracts([article for _, _, article in games], lang)
        source = _("Source: Wikipedia, CC BY-SA 4.0")
        return [
            GameRecord(
                provider=self.name,
                external_id=qid,
                title=DISAMBIGUATION.sub("", article),
                first_release_date=_first_release(entity),
                summary=f"{extracts[article]}\n\n{source}" if extracts.get(article) else "",
            )
            for qid, entity, article in games
        ]

    def _extracts(self, titles: list[str], lang: str) -> dict[str, str]:
        """The articles' introductions as plain text, by title. A title that only redirects
        to another article (de: "Game Boy Color" → "Game Boy") has none: unresolved,
        Wikipedia answers with the redirect page's own text ("Wikidata: …"), resolved with
        an article about something else."""
        if not titles:
            return {}
        data = self._get(
            WIKIPEDIA_API.format(language=lang),
            {
                "action": "query",
                "prop": "extracts",
                "exintro": "1",
                "explaintext": "1",
                "exlimit": "20",
                "titles": "|".join(titles),
                "redirects": "1",
                "formatversion": "2",
            },
        )
        return {
            str(page["title"]): str(page.get("extract", "")).strip()
            for page in data.get("query", {}).get("pages", [])
            if page.get("title")
        }
