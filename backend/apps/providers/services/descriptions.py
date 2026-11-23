"""Descriptions of companies, series, franchises and platforms from a source (Wikipedia,
IGDB): admins
pick the right entry, its text becomes the description, its logo (if wanted) the picture,
and the entry is remembered. A company also takes the entry's facts – what the entry knows
replaces ours, what it doesn't know stays – and is linked to its parent and subsidiaries
that are in the catalog already (none are created). A platform fills its short name,
manufacturer and year only where they're empty (badges and grouping use them), takes
generation and end of production, and is linked to predecessors and successors in the
catalog. A series without a franchise gets the entry's, if it's in the catalog.

The pictures of the entries something is linked to (every logo a Wikidata entry lists,
photos of a platform, the IGDB logo …) can be chosen later – a platform's as its picture
or as its badge's icon; they reach the browser only as encrypted tokens."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from ninja.errors import HttpError

from apps.catalog.models import Company, Franchise, Platform, Series
from apps.catalog.selectors.terms import description_for
from apps.catalog.services.platforms import note_icon
from apps.catalog.services.terms import check_parent, clean_country, clean_website
from apps.catalog.services.tones import note_tones
from apps.core.services.images import (
    ICON_TYPES,
    fit_picture,
    icon_extension,
    make_icon,
    store_icon,
)

from ..sources import ProviderError
from ..sources.base import (
    CompanyFacts,
    DescriptionRecord,
    DescriptionSource,
    EntryRef,
    PlatformFacts,
)
from ..sources.names import normalize
from ..sources.registry import description_source
from ..sources.wikipedia import WikipediaSource
from .integrations import decrypt, encrypt

# What can be described (genres are too general for an article).
KINDS: dict[str, type[Company] | type[Series] | type[Franchise] | type[Platform]] = {
    "companies": Company,
    "series": Series,
    "franchises": Franchise,
    "platforms": Platform,
}
Term = Company | Series | Franchise | Platform
# Where a picture goes: the picture (a term's, a platform's logo), a platform's photo of
# the device or its badge's icon.
TARGETS = ("image", "photo", "icon")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Applied:
    description: str
    image: bool  # whether the entry's logo became the picture


@dataclass(frozen=True)
class ImageCandidate:
    source: str
    label: str
    kind: str  # "logo", "icon" (a small logo) or "photo"
    token: str  # the source and the image's URL, encrypted


def kind_of(term: Term) -> str:
    return next(k for k, model in KINDS.items() if isinstance(term, model))


def _stored_id(term: Term, key: str, external_id: str) -> str | int:
    """Platforms keep IGDB's ids as numbers: imports find them by those."""
    return int(external_id) if isinstance(term, Platform) and key == "igdb" else external_id


def _source(key: str) -> DescriptionSource:
    source = description_source(key)
    if source is None:
        raise HttpError(400, _("This integration is switched off."))
    return source


def candidates(kind: str, term: Term, key: str, query: str = "") -> list[DescriptionRecord]:
    try:
        return _source(key).describe(query.strip() or term.name, kind, get_language())
    except ProviderError as exc:
        raise HttpError(502, _("The source did not answer. Try again later.")) from exc


def apply(term: Term, key: str, external_id: str, image: bool = False) -> Applied:
    """Fetches the entry again (a client can only pick, never send text or URLs) and takes
    it: its texts replace ours in their languages (others stay), with `image` its logo
    replaces the picture. A logo that can't be loaded or used (an SVG with scripts …) is
    skipped – the rest is still taken. A company entry without any article gives facts
    only."""
    source = _source(key)
    try:
        record = source.description(external_id, get_language(), kind_of(term))
    except ProviderError as exc:
        raise HttpError(502, _("The source did not answer. Try again later.")) from exc
    if record is None or not (
        record.texts or record.company or record.platform or record.franchise or record.image_url
    ):
        raise HttpError(404, _("The source has no text for this entry."))
    term.descriptions = {**term.descriptions, **record.texts}
    term.external_ids = {
        **term.external_ids,
        key: _stored_id(term, key, record.external_id),
    }
    fields = ["descriptions", "external_ids"]
    took_image = image and _take_logo(term, source, record)
    if took_image:
        fields.append("image")
    fields += _take_record_facts(term, record, key)
    term.save(update_fields=fields)
    if took_image:
        note_tones(term)
    return Applied(description_for(term.descriptions)[0], took_image)


def _take_logo(term: Term, source: DescriptionSource, record: DescriptionRecord) -> bool:
    """Stores the entry's logo as the term's picture; False if there is none or it can't
    be loaded or used."""
    if not record.image_url:
        return False
    try:
        data = fit_picture(source.image(record.image_url))
        store_icon(term.image, SimpleUploadedFile("logo", data), max_kb=2048, logo=True)
    except (ProviderError, HttpError) as exc:
        logger.warning("Logo %s not taken: %s", record.image_url, exc)
        return False
    return True


def _take_record_facts(term: Term, record: DescriptionRecord, key: str) -> list[str]:
    """What the entry knows besides texts, by the kind of term; returns changed fields."""
    if isinstance(term, Company) and record.company is not None:
        return _take_facts(term, record.company, key)
    if isinstance(term, Platform) and record.platform is not None:
        return _take_platform_facts(term, record.platform, key)
    if isinstance(term, Series) and record.franchise and not term.franchise_id:
        franchise = _find_franchise(record.franchise, key)
        if franchise is not None:
            term.franchise = franchise
            return ["franchise"]
    return []


def _find(ref: EntryRef, key: str) -> Company | None:
    """The catalog's company for an entry: by the remembered id, else by a name."""
    found = Company.objects.filter(**{f"external_ids__{key}": ref.external_id}).first()
    for name in ref.names:
        found = found or Company.objects.filter(name__iexact=name).order_by("name").first()
    return found


def _find_franchise(ref: EntryRef, key: str) -> Franchise | None:
    """The catalog's franchise for an entry: by the remembered id, else by a name."""
    found = Franchise.objects.filter(**{f"external_ids__{key}": ref.external_id}).first()
    for name in ref.names:
        found = found or Franchise.objects.filter(name__iexact=name).order_by("name").first()
    return found


def _fits(company: Company, parent: Company) -> bool:
    try:
        check_parent(company, parent)
    except HttpError:
        return False
    return True


def _take_facts(company: Company, facts: CompanyFacts, key: str) -> list[str]:
    """Sets what the entry knows (unchecked values are skipped); returns changed fields.
    Subsidiaries without a parent get this company."""
    fields: list[str] = []

    def put(name: str, value: object) -> None:
        if value not in (None, ""):
            setattr(company, name, value)
            fields.append(name)

    put("founded", facts.founded)
    put("dissolved", facts.dissolved)
    put("headquarters", facts.headquarters[:200])
    for name, value, clean_value in (
        ("country", facts.country, clean_country),
        ("website", facts.website, clean_website),
    ):
        try:
            put(name, clean_value(value))
        except HttpError:
            logger.warning("Skipping %s %r from %s", name, value, key)
    parent = _find(facts.parent, key) if facts.parent else None
    if parent is not None and _fits(company, parent):
        put("parent", parent)
    for ref in facts.subsidiaries:
        child = _find(ref, key)
        if child is not None and child.parent_id is None and _fits(child, company):
            child.parent = company
            child.save(update_fields=["parent"])
    return fields


def _platform_names(platform: Platform) -> set[str]:
    """Its name, short name and name without the maker ("Nintendo Wii U" → "Wii U")."""
    names = {platform.name, platform.short_name}
    if platform.manufacturer and platform.name.lower().startswith(platform.manufacturer.lower()):
        names.add(platform.name[len(platform.manufacturer) :])
    return {normalize(n) for n in names if n.strip()}


def _find_platform(ref: EntryRef, key: str) -> Platform | None:
    """The catalog's platform for an entry: by the remembered id, else by a name."""
    stored = int(ref.external_id) if key == "igdb" and ref.external_id.isdigit() else None
    found = Platform.objects.filter(
        **{f"external_ids__{key}": stored if stored is not None else ref.external_id}
    ).first()
    if found is None:
        wanted = {normalize(n) for n in ref.names}
        found = next(
            (p for p in Platform.objects.order_by("name") if _platform_names(p) & wanted), None
        )
    return found


def _take_platform_facts(platform: Platform, facts: PlatformFacts, key: str) -> list[str]:
    """Fills short name, manufacturer (the catalog company's name if it's there) and year
    where empty; sets generation and end of production where known; links predecessors
    and successors that are in the catalog. Returns changed fields."""
    fields: list[str] = []
    maker = ""
    if facts.manufacturer:
        company = _find(facts.manufacturer, key)
        maker = company.name if company else facts.manufacturer.names[0]
    for name, value in (
        ("short_name", facts.short_name),
        ("manufacturer", maker[:100]),
        ("release_year", facts.released),
    ):
        if value and not getattr(platform, name):
            setattr(platform, name, value)
            fields.append(name)
    for name, value in (("generation", facts.generation), ("discontinued", facts.discontinued)):
        if value:
            setattr(platform, name, value)
            fields.append(name)
    for refs, relation in (
        (facts.predecessors, platform.predecessors),
        (facts.successors, platform.successors),
    ):
        others = [p for ref in refs if (p := _find_platform(ref, key)) and p.pk != platform.pk]
        if others:
            relation.add(*others)
    return fields


def images(term: Term) -> list[ImageCandidate]:
    """Every picture the entries the term is linked to offer, by source. A source that
    doesn't answer is left out."""
    kind = kind_of(term)
    found: list[ImageCandidate] = []
    for key, external_id in sorted(term.external_ids.items()):
        source = description_source(key)
        if source is None:
            continue
        try:
            record = source.description(str(external_id), get_language(), kind)
        except ProviderError as exc:
            logger.warning("No pictures from %s: %s", key, exc)
            continue
        for option in record.images if record else ():
            token = encrypt(json.dumps({"source": key, "url": option.url}))
            found.append(ImageCandidate(key, option.label, option.kind, token))
    return found


def image(token: str) -> tuple[bytes, str]:
    """The picture behind a token, checked like an upload: (bytes, content type)."""
    raw = decrypt(token)
    try:
        data = json.loads(raw) if raw else {}
    except ValueError:
        data = {}
    source = description_source(str(data.get("source", "")))
    if source is None or not isinstance(data.get("url"), str):
        raise HttpError(400, _("Unknown picture."))
    try:
        content = fit_picture(source.image(data["url"]))
    except ProviderError as exc:
        logger.warning("Picture not loaded: %s", exc)
        raise HttpError(502, _("The picture couldn't be loaded.")) from exc
    return content, ICON_TYPES[icon_extension(content)]


def search_images(query: str) -> list[ImageCandidate]:
    """Pictures on Wikimedia Commons for a query (an icon, a photo of the device …)."""
    source = _source("wikipedia")
    if not isinstance(source, WikipediaSource) or not query.strip():
        return []
    try:
        options = source.search_images(query.strip())
    except ProviderError as exc:
        raise HttpError(502, _("The source did not answer. Try again later.")) from exc
    return [
        ImageCandidate(
            "wikipedia",
            o.label,
            o.kind,
            encrypt(json.dumps({"source": "wikipedia", "url": o.url})),
        )
        for o in options
    ]


def take_image(term: Term, token: str, target: str = "image") -> Term:
    """Makes the picture behind the token the term's picture or – platforms only – the
    photo of the device or its badge's icon (a raster picture is freed from a plain
    background and cut to size: a photo of the device makes an icon)."""
    if target not in TARGETS or (target != "image" and not isinstance(term, Platform)):
        raise HttpError(400, _("Unknown picture."))
    content, _type = image(token)
    if isinstance(term, Platform) and target == "icon":
        content = make_icon(content)
    field = term.image
    if isinstance(term, Platform) and target != "image":
        field = term.icon_image if target == "icon" else term.photo
    store_icon(field, SimpleUploadedFile("logo", content), max_kb=2048, logo=target == "image")
    if isinstance(term, Platform) and target == "icon":
        return note_icon(term)
    term.save(update_fields=[field.field.name])
    return note_tones(term)
