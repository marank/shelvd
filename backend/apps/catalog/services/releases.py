"""Creating and editing catalog entries by hand, and attaching barcodes and covers."""

from __future__ import annotations

from uuid import UUID

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils.translation import gettext as _
from ninja.errors import HttpError

from apps.accounts.models import User
from apps.core.services.images import store_image
from apps.providers.services import gtin

from ..models import (
    COVER_FIELDS,
    Barcode,
    Company,
    Franchise,
    Genre,
    Platform,
    Release,
    Series,
    Work,
)
from ..schemas import ReleaseIn, ReleasePatch, WorkPatch
from . import terms
from .review import stamp


def _platform(platform_id: UUID) -> Platform:
    platform = Platform.objects.filter(pk=platform_id).first()
    if platform is None:
        raise HttpError(400, _("Unknown platform."))
    return platform


@transaction.atomic
def create_release(data: ReleaseIn, user: User) -> Release:
    title = data.title.strip()
    if not title:
        raise HttpError(400, _("A title is required."))
    if data.work_id:
        work = Work.objects.filter(pk=data.work_id).first()
        if work is None:
            raise HttpError(400, _("Unknown work."))
    else:
        work = Work(title=title, summary=data.summary)
        stamp(work, user)
        work.save()
        work.genres.set(terms.resolve(Genre, data.genres))
        work.developers.set(terms.resolve(Company, data.developers))
        work.series.set(terms.resolve(Series, data.series))
        work.franchises.set(terms.resolve(Franchise, data.franchises))
    release = Release(
        work=work,
        platform=_platform(data.platform_id),
        region=data.region,
        title=title if title != work.title else "",
        edition=data.edition.strip(),
        age_rating=data.age_rating.strip(),
        product_code=data.product_code.strip(),
        release_number=data.release_number,
        release_date=data.release_date,
        release_date_end=data.release_date_end,
        release_precision=data.release_precision,
        publisher=terms.resolve_one(Company, data.publisher),
    )
    stamp(release, user)
    release.save()
    if data.barcode:
        attach_barcode(release, data.barcode, user, source="manual")
    return release


@transaction.atomic
def update_release(release: Release, data: ReleasePatch) -> Release:
    fields = data.model_dump(exclude_unset=True)
    if fields.get("title") is not None:
        title = fields["title"].strip()
        release.title = "" if title == release.work.title else title
    if fields.get("platform_id"):
        release.platform = _platform(fields["platform_id"])
    for name in ("region", "release_precision", "age_rating", "product_code"):
        if fields.get(name) is not None:
            setattr(release, name, fields[name])
    if fields.get("edition") is not None:
        release.edition = terms.clean(fields["edition"])
    for name in ("release_date", "release_date_end", "release_number"):  # may be cleared
        if name in fields:
            setattr(release, name, fields[name])
    if "publisher" in fields:
        release.publisher = terms.resolve_one(Company, data.publisher)
    release.save()
    if data.release_developers is not None:
        release.developers.set(terms.resolve(Company, data.release_developers))
    return release


@transaction.atomic
def update_work(work: Work, data: WorkPatch) -> Work:
    fields = data.model_dump(exclude_unset=True)
    if fields.get("title") is not None:
        title = fields["title"].strip()
        if not title:
            raise HttpError(400, _("A title is required."))
        work.title = title
    if fields.get("summary") is not None:
        work.summary = fields["summary"]
    if "first_release_date" in fields:
        work.first_release_date = fields["first_release_date"]
    work.save()
    if data.genres is not None:
        work.genres.set(terms.resolve(Genre, data.genres))
    if data.developers is not None:
        work.developers.set(terms.resolve(Company, data.developers))
    if data.series is not None:
        work.series.set(terms.resolve(Series, data.series))
    if data.franchises is not None:
        work.franchises.set(terms.resolve(Franchise, data.franchises))
    return work


def attach_barcode(release: Release, raw: str, user: User | None, *, source: str) -> Barcode:
    code = gtin.normalize_code(raw)
    if code is None:
        raise HttpError(400, _("This is not a valid barcode."))
    existing = Barcode.objects.filter(code=code).first()
    if existing is not None:
        if existing.release_id != release.pk:
            raise HttpError(409, _("This barcode already belongs to another release."))
        return existing
    barcode = Barcode(code=code, release=release, source=source, confirmed_by=user)
    stamp(barcode, user)
    barcode.save()
    return barcode


def set_work_cover(work: Work, upload: UploadedFile[bytes], max_mb: int) -> Work:
    """A general cover for the game; replaces its previous one."""
    store_image(work.cover, upload, max_mb)
    work.save(update_fields=[*COVER_FIELDS, "updated_at"])
    return work


def remove_work_cover(work: Work) -> Work:
    if work.cover:
        work.cover.delete(save=False)
    work.save(update_fields=[*COVER_FIELDS, "updated_at"])
    return work


def set_cover(release: Release, upload: UploadedFile[bytes], max_mb: int) -> Release:
    store_image(release.cover, upload, max_mb)
    release.cover_source = "upload"
    release.save(update_fields=[*COVER_FIELDS, "cover_source", "updated_at"])
    return release
