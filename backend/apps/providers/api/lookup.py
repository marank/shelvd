from uuid import UUID

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from ninja import Router, Status
from ninja.errors import HttpError

from apps.accounts.api.auth import current_user
from apps.catalog.api.catalog import releases
from apps.catalog.models import Platform, Release
from apps.catalog.schemas import ReleaseOut
from apps.catalog.services.releases import attach_barcode
from apps.collection.services.access import require_contributor
from apps.core.api.errors import ErrorOut

from ..schemas import (
    BarcodeLookupOut,
    CandidateOut,
    ImportIn,
    ProviderOut,
    SearchOut,
)
from ..services import gtin, lookup
from ..services.importer import import_record
from ..services.integrations import DEFINITIONS, config
from ..sources import ProviderError, metadata_source

router = Router(tags=["lookup"])
ERRORS = {400: ErrorOut, 404: ErrorOut, 409: ErrorOut, 502: ErrorOut}


def candidate_out(candidate: lookup.Candidate) -> CandidateOut:
    record = candidate.record
    released = record.release_date or record.first_release_date
    return CandidateOut(
        provider=record.provider,
        external_id=record.external_id,
        title=record.title,
        platform_id=candidate.platform.pk if candidate.platform else None,
        platform_name=candidate.platform.name if candidate.platform else record.platform_name,
        region=record.region,
        release_date=record.release_date,
        release_precision=record.release_precision,
        year=released.year if released else None,
        publisher=record.publisher,
        developers=record.developers,
        genres=record.genres,
        summary=record.summary,
        cover_url=record.cover_url,
    )


def search_out(result: lookup.SearchResult) -> SearchOut:
    return SearchOut(
        query=result.query,
        platform_id=result.platform.pk if result.platform else None,
        candidates=[candidate_out(c) for c in result.candidates],
        errors=result.errors,
    )


@router.get("providers", response=list[ProviderOut])
def providers(request: HttpRequest) -> list[ProviderOut]:
    """Which external services are switched on and set up, so the UI can explain
    missing results and credit them."""
    return [
        ProviderOut(name=d.key, label=d.name, kind=d.kind, enabled=config(d.key).active)
        for d in DEFINITIONS.values()
    ]


@router.get("barcode/{code}", response={200: BarcodeLookupOut, **ERRORS})
def barcode(request: HttpRequest, code: str) -> BarcodeLookupOut:
    normalized = gtin.normalize_code(code)
    if normalized is None:
        raise HttpError(400, _("This is not a valid barcode."))
    result = lookup.lookup_barcode(normalized)
    known_ids = [release.pk for release in result.known]
    return BarcodeLookupOut(
        code=result.code,
        known=list(releases().filter(pk__in=known_ids)),  # type: ignore[arg-type]
    )


@router.get("search", response={200: SearchOut, **ERRORS})
def search(request: HttpRequest, q: str, platform: UUID | None = None) -> SearchOut:
    if not q.strip():
        raise HttpError(400, _("Enter a title to search for."))
    platform_obj = get_object_or_404(Platform, pk=platform) if platform else None
    return search_out(lookup.search(q.strip(), platform_obj))


@router.post("import", response={201: ReleaseOut, **ERRORS})
def import_candidate(request: HttpRequest, payload: ImportIn) -> Status[Release]:
    """Store a provider record as a release (fetched again from the provider, so the
    client can't inject data), optionally confirming the scanned barcode for it (the
    barcode waits for an admin's review)."""
    user = current_user(request)
    require_contributor(user)
    source = metadata_source(payload.provider, catalog=True)
    if source is None:
        raise HttpError(400, _("This source is not configured."))
    platform = get_object_or_404(Platform, pk=payload.platform_id)
    platform_external_id = platform.external_ids.get(source.name)
    try:
        record = source.get(
            payload.external_id,
            str(platform_external_id) if platform_external_id else None,
            language=get_language(),
        )
    except ProviderError as exc:
        raise HttpError(502, _("The source did not answer. Try again later.")) from exc
    if record is None:
        raise HttpError(404, _("The source does not know this game."))
    release = import_record(record, platform, payload.region, user)
    if payload.barcode:
        attach_barcode(release, payload.barcode, user, source="scan")
    return Status(201, releases().get(pk=release.pk))
