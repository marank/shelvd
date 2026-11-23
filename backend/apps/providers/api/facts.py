"""Play times and scores of a game, and covers from covers sources (mounted under /catalog).

Refreshing what's outdated happens for everyone; choosing a match, forcing a refresh or
taking a release cover is for admins (the catalog is theirs). Copies take covers through
the items API."""

from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Router, Status

from apps.accounts.api.auth import current_user
from apps.accounts.selectors import require_admin
from apps.catalog.models import Release, Work
from apps.catalog.schemas import FactOut, ReleaseOut
from apps.collection.services.access import require_contributor
from apps.core.api.errors import ErrorOut

from ..schemas import CoverCandidateOut, CoverIn, FactCandidateOut, PinIn
from ..services import covers, facts

router = Router(tags=["facts"])
ERRORS = {400: ErrorOut, 404: ErrorOut, 502: ErrorOut}


@router.post("works/{work_id}/facts/refresh", response={200: dict[str, bool], **ERRORS})
def refresh_facts(request: HttpRequest, work_id: UUID, force: bool = False) -> dict[str, bool]:
    """Opening a game asks for this: whatever is older than its max age is fetched again
    (`force`: everything). Answers whether anything was fetched."""
    work = get_object_or_404(Work, pk=work_id)
    if force:
        require_admin(current_user(request))
        changed = any(facts.refresh(work, key, force=True) for key in facts.FACT_SOURCES)
    else:
        changed = facts.refresh_work(work)
    return {"refreshed": changed}


@router.get(
    "works/{work_id}/facts/{source}/candidates",
    response={200: list[FactCandidateOut], **ERRORS},
)
def fact_candidates(
    request: HttpRequest, work_id: UUID, source: str, q: str = ""
) -> list[FactCandidateOut]:
    require_admin(current_user(request))
    work = get_object_or_404(Work, pk=work_id)
    return [
        FactCandidateOut(
            external_id=r.external_id,
            title=r.title,
            url=r.url,
            year=r.year,
            platforms=r.platforms,
            values=r.values,
        )
        for r in facts.candidates(work, source, q)
    ]


@router.put("works/{work_id}/facts/{source}", response={200: FactOut, **ERRORS})
def pin_fact(request: HttpRequest, work_id: UUID, source: str, payload: PinIn) -> FactOut:
    require_admin(current_user(request))
    fact = facts.pin(get_object_or_404(Work, pk=work_id), source, payload.external_id)
    return FactOut.model_validate(fact, from_attributes=True)


@router.delete("works/{work_id}/facts/{source}", response={204: None, **ERRORS})
def unpin_fact(request: HttpRequest, work_id: UUID, source: str) -> Status[None]:
    require_admin(current_user(request))
    facts.unpin(get_object_or_404(Work, pk=work_id), source)
    return Status(204, None)


@router.get(
    "releases/{release_id}/cover-candidates",
    response={200: list[CoverCandidateOut], **ERRORS},
)
def cover_candidates(
    request: HttpRequest, release_id: UUID, q: str = ""
) -> list[CoverCandidateOut]:
    """`q` searches for something else than the game's title. For a release's cover
    (admins) or a copy's own cover (editors)."""
    require_contributor(current_user(request))
    release = get_object_or_404(Release.objects.select_related("work", "platform"), pk=release_id)
    return [
        CoverCandidateOut(
            source=c.record.source,
            title=c.record.title,
            region=c.record.region,
            platform=c.record.platform,
            width=c.record.width,
            height=c.record.height,
            token=c.token,
        )
        for c in covers.candidates(release, q)
    ]


@router.get("cover-preview", response={200: None, **ERRORS})
def cover_preview(request: HttpRequest, token: str) -> HttpResponse:
    require_contributor(current_user(request))
    content, content_type = covers.fetch(token)
    response = HttpResponse(content, content_type=content_type)
    response["Cache-Control"] = "private, max-age=3600"
    return response


@router.post("releases/{release_id}/cover-from", response={200: ReleaseOut, **ERRORS})
def cover_from(request: HttpRequest, release_id: UUID, payload: CoverIn) -> Release:
    require_admin(current_user(request))
    release = get_object_or_404(Release, pk=release_id)
    return covers.apply(release, payload.token)
