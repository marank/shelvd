"""Turning names and picked references into catalog terms (companies, genres, series).

A name finds the existing term in any case ("level-5" is "Level-5") and only creates one
when there's none, so typing never makes near-duplicates. Spaces are normalised.
"""

from __future__ import annotations

from typing import cast

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import URLValidator
from django.db import transaction
from django.utils.translation import gettext as _
from ninja.errors import HttpError

from apps.core.services.images import store_icon

from ..models import Company, Franchise, Genre, Release, Series, Work
from ..schemas import CompanyDetailsIn, SeriesDetailsIn, TermRef
from .tones import note_tones

type Term = Company | Genre | Series | Franchise


def clean(name: str) -> str:
    return " ".join(name.split())


def by_name[T: Term](model: type[T], name: str) -> T | None:
    """The term with this name (any case), created if there's none; None for blank."""
    max_length = model._meta.get_field("name").max_length
    name = clean(name)[:max_length].rstrip()  # cut first, or a long name is never found
    if not name:
        return None
    existing = model.objects.filter(name__iexact=name).order_by("name").first()
    return cast(T, existing or model.objects.create(name=name))


def by_names[T: Term](model: type[T], names: list[str]) -> list[T]:
    return _unique([term for n in names if (term := by_name(model, n)) is not None])


def resolve[T: Term](model: type[T], refs: list[TermRef]) -> list[T]:
    """Picked terms: existing ones by id (400 if unknown), new ones by name."""
    terms: list[T] = []
    for ref in refs:
        if ref.id is not None:
            term = model.objects.filter(pk=ref.id).first()
            if term is None:
                raise HttpError(400, _("A picked entry doesn't exist (any more)."))
            terms.append(cast(T, term))
        elif (named := by_name(model, ref.name)) is not None:
            terms.append(named)
    return _unique(terms)


def resolve_one[T: Term](model: type[T], ref: TermRef | None) -> T | None:
    return next(iter(resolve(model, [ref])), None) if ref is not None else None


def _unique[T: Term](terms: list[T]) -> list[T]:
    seen: set[object] = set()
    unique = []
    for term in terms:
        if term.pk not in seen:
            seen.add(term.pk)
            unique.append(term)
    return unique


def update(term: Term, name: str | None = None, descriptions: dict[str, str] | None = None) -> Term:
    """A new name (409 if another term has it, in any case – merge them instead) and/or
    descriptions by language."""
    fields = []
    if name is not None:
        name = clean(name)
        if not name:
            raise HttpError(400, _("The name can't be empty."))
        try:  # the field's max_length (Django's own, translated message)
            type(term)._meta.get_field("name").run_validators(name)
        except ValidationError as error:
            raise HttpError(400, error.messages[0]) from error
        if type(term).objects.filter(name__iexact=name).exclude(pk=term.pk).exists():
            raise HttpError(
                409, _("“%(name)s” already exists. Merge the two instead.") % {"name": name}
            )
        term.name = name
        fields.append("name")
    if descriptions is not None:
        term.descriptions = merge_descriptions(term.descriptions, descriptions)
        fields.append("descriptions")
    if fields:
        term.save(update_fields=fields)
    return term


def merge_descriptions(current: dict[str, str], new: dict[str, str]) -> dict[str, str]:
    """`new` texts over `current` ones, by language; empty ones remove theirs. Only the
    site's languages (400 otherwise)."""
    languages = {code for code, _name in settings.LANGUAGES}
    if unknown := set(new) - languages:
        raise HttpError(400, _("Unknown language: %(code)s") % {"code": ", ".join(sorted(unknown))})
    merged = {**current, **{code: text.strip() for code, text in new.items()}}
    return {code: text for code, text in merged.items() if text}


COMPANY_FIELDS = ["founded", "dissolved", "country", "headquarters", "website", "parent"]


def check_parent(company: Company, parent: Company | None) -> None:
    """A company can't be its own parent, not even further up (400)."""
    seen = parent
    while seen is not None:
        if seen.pk == company.pk:
            raise HttpError(400, _("A company can't belong to itself."))
        seen = seen.parent


def clean_website(url: str) -> str:
    """An http(s) address or ""; 400 for anything else (javascript: …)."""
    url = url.strip()
    if not url:
        return ""
    try:
        URLValidator(schemes=["http", "https"])(url)
    except ValidationError as error:
        raise HttpError(400, _("The website must be an http(s) address.")) from error
    return url


def clean_country(code: str) -> str:
    code = code.strip().upper()
    if code and not (len(code) == 2 and code.isascii() and code.isalpha()):
        raise HttpError(400, _("The country must be a two-letter code (DE, JP …)."))
    return code


def set_company_details(company: Company, data: CompanyDetailsIn) -> Company:
    """Years, country, seat, website and parent, all at once."""
    for year in (data.founded, data.dissolved):
        if year is not None and not 1000 <= year <= 9999:
            raise HttpError(400, _("Years have four digits."))
    if data.founded and data.dissolved and data.dissolved < data.founded:
        raise HttpError(400, _("A company can't be dissolved before it was founded."))
    parent = resolve_one(Company, data.parent)
    check_parent(company, parent)
    company.founded = data.founded
    company.dissolved = data.dissolved
    company.country = clean_country(data.country)
    company.headquarters = clean(data.headquarters)[:200]
    company.website = clean_website(data.website)
    company.parent = parent
    company.save(update_fields=COMPANY_FIELDS)
    return company


def set_series_details(series: Series, data: SeriesDetailsIn) -> Series:
    """A series' franchise: an existing one (by id or name) or none."""
    series.franchise = resolve_one(Franchise, data.franchise)
    series.save(update_fields=["franchise"])
    return series


def set_image(term: Term, upload: UploadedFile[bytes]) -> Term:
    """A logo or picture: SVG (checked for scripts and links) or JPEG/PNG/WebP, ≤ 2 MB."""
    store_icon(term.image, upload, max_kb=2048, logo=True)
    term.save(update_fields=["image"])
    return note_tones(term)


def remove_image(term: Term) -> Term:
    if term.image:
        term.image.delete(save=False)
    term.save(update_fields=["image"])
    return note_tones(term)


def delete(term: Term) -> None:
    """Games and releases just lose it; its picture goes too."""
    if term.image:
        term.image.delete(save=False)
    term.delete()


@transaction.atomic
def merge[T: Term](source: T, target: T) -> T:
    """Everything that uses `source` uses `target` afterwards; `source` is deleted."""
    if source.pk == target.pk:
        raise HttpError(400, _("An entry can't be merged into itself."))
    _move_uses(source, target)
    # What the target lacks it takes over: foreign ids (IGDB …), description, picture.
    target.external_ids = {**source.external_ids, **target.external_ids}
    target.descriptions = {**source.descriptions, **target.descriptions}
    if not target.image and source.image:
        target.image.name, source.image.name = source.image.name, ""
        target.image_tone = source.image_tone
    fields = ["external_ids", "descriptions", "image", "image_tone"]
    if isinstance(source, Company) and isinstance(target, Company):
        fields += _take_company_facts(source, target)
    if isinstance(source, Series) and isinstance(target, Series) and not target.franchise_id:
        target.franchise_id = source.franchise_id
        fields.append("franchise")
    target.save(update_fields=fields)
    delete(source)
    return target


def _move_uses(source: Term, target: Term) -> None:
    """Games, releases (and series of a franchise) that use `source` use `target`."""
    if isinstance(source, Company):
        Release.objects.filter(publisher=source).update(publisher=target)
        _relink(Work.developers.through, "company", source, target)
        _relink(Release.developers.through, "company", source, target, "release_id")
    elif isinstance(source, Genre):
        _relink(Work.genres.through, "genre", source, target)
    elif isinstance(source, Franchise):
        _relink(Work.franchises.through, "franchise", source, target)
        Series.objects.filter(franchise=source).update(franchise=target)
    else:
        _relink(Work.series.through, "series", source, target)


def _take_company_facts(source: Company, target: Company) -> list[str]:
    """The target takes over the source's subsidiaries and the facts it lacks; returns the
    fields to save."""
    source.subsidiaries.exclude(pk=target.pk).update(parent=target)
    for name in COMPANY_FIELDS:
        if getattr(target, name) in (None, ""):
            setattr(target, name, getattr(source, name))
    if target.parent_id in (source.pk, target.pk):
        target.parent = None
    return list(COMPANY_FIELDS)


def _relink(through: type, field: str, source: Term, target: Term, owner: str = "work_id") -> None:
    """Point the source's links at the target, without doubling an existing link of the
    same game (or release: `owner`)."""
    links = through.objects  # type: ignore[attr-defined]
    has_target = links.filter(**{field: target}).values(owner)
    links.filter(**{field: source}, **{f"{owner}__in": has_target}).delete()
    links.filter(**{field: source}).update(**{field: target})
