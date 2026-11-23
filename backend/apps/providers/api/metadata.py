"""Matching a catalog game with a metadata source: candidates, what would change, and
applying the changes people chose (mounted under /catalog). Admins only: it changes the
catalog."""

from dataclasses import asdict
from uuid import UUID

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router

from apps.accounts.api.auth import current_user
from apps.accounts.selectors import require_admin
from apps.catalog.models import Work
from apps.core.api.errors import ErrorOut

from ..schemas import (
    MetadataApplyIn,
    MetadataApplyOut,
    MetadataCandidateOut,
    MetadataChangeOut,
    MetadataPreviewOut,
    MetadataValueOut,
)
from ..services import metadata

router = Router(tags=["metadata"])
ERRORS = {400: ErrorOut, 404: ErrorOut, 502: ErrorOut}


@router.get(
    "works/{work_id}/metadata/{source}/candidates",
    response={200: list[MetadataCandidateOut], **ERRORS},
)
def metadata_candidates(
    request: HttpRequest, work_id: UUID, source: str, q: str = ""
) -> list[MetadataCandidateOut]:
    require_admin(current_user(request))
    work = get_object_or_404(Work, pk=work_id)
    return [
        MetadataCandidateOut(
            external_id=c.record.external_id,
            title=c.record.title,
            year=c.record.first_release_date.year if c.record.first_release_date else None,
            platforms=c.platforms,
            summary=c.record.summary,
            cover_url=c.record.cover_url,
        )
        for c in metadata.candidates(work, source, q)
    ]


@router.get(
    "works/{work_id}/metadata/{source}/{external_id}",
    response={200: MetadataPreviewOut, **ERRORS},
)
def metadata_preview(
    request: HttpRequest, work_id: UUID, source: str, external_id: str
) -> MetadataPreviewOut:
    """What the source's game would change: current against proposed, field by field."""
    require_admin(current_user(request))
    result = metadata.preview(get_object_or_404(Work, pk=work_id), source, external_id)
    return MetadataPreviewOut(
        external_id=result.record.external_id,
        title=result.record.title,
        changes=[
            MetadataChangeOut(
                id=c.id,
                field=c.field,
                kind=c.kind,
                suggested=c.suggested,
                release_id=c.release.pk if c.release else None,
                current=MetadataValueOut(**asdict(c.current)),
                proposed=MetadataValueOut(**asdict(c.proposed)),
            )
            for c in result.changes
        ],
    )


@router.post("works/{work_id}/metadata/{source}", response={200: MetadataApplyOut, **ERRORS})
def apply_metadata(
    request: HttpRequest, work_id: UUID, source: str, payload: MetadataApplyIn
) -> MetadataApplyOut:
    """Link the game to the entry and apply the chosen changes (by id from the preview)."""
    require_admin(current_user(request))
    work = get_object_or_404(Work, pk=work_id)
    return MetadataApplyOut(
        applied=metadata.apply(work, source, payload.external_id, payload.changes)
    )
