from typing import Literal
from uuid import UUID

from django.conf import settings
from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import File, Router, Status, UploadedFile

from apps.accounts.api.auth import current_user
from apps.accounts.selectors import require_admin
from apps.collection.services.access import require_contributor
from apps.core.api.errors import ErrorOut
from apps.providers.services import gtin

from .. import selectors
from ..models import Platform, Release, Work
from ..schemas import (
    BarcodeIn,
    EditionOut,
    MergeWorkIn,
    MoveReleaseIn,
    PlatformDetailOut,
    PlatformGamesOut,
    PlatformIn,
    PlatformListOut,
    PlatformPatch,
    ReleaseIn,
    ReleaseOut,
    ReleasePatch,
    WorkOut,
    WorkPatch,
    WorkSummaryOut,
)
from ..selectors.terms import Edition, PlatformGames
from ..selectors.works import WorkSummary
from ..services import platforms as platform_service
from ..services import releases as service
from ..services.merge import merge_works, move_release
from ..services.platforms import PICTURES
from ..services.review import require_edit

router = Router(tags=["catalog"])

ERRORS = {400: ErrorOut, 404: ErrorOut, 409: ErrorOut}


def releases() -> QuerySet[Release]:
    return Release.objects.select_related("work", "platform", "publisher").prefetch_related(
        "work__genres",
        "work__developers",
        "work__series",
        "work__franchises",
        "barcodes",
        "developers",
    )


@router.get("platforms", response=list[PlatformListOut])
def list_platforms(request: HttpRequest) -> QuerySet[Platform]:
    """Every platform with its pictures, facts and number of games in the catalog."""
    return Platform.objects.annotate(game_count=Count("releases__work", distinct=True))


# Platforms, like the whole catalog, are kept by admins.
@router.post("platforms", response={201: PlatformDetailOut, **ERRORS})
def create_platform(request: HttpRequest, payload: PlatformIn) -> Status[Platform]:
    require_admin(current_user(request))
    return Status(201, platform_service.create_platform(payload))


@router.get("platforms/{platform_id}", response={200: PlatformDetailOut, 404: ErrorOut})
def get_platform(request: HttpRequest, platform_id: UUID) -> Platform:
    return get_object_or_404(Platform, pk=platform_id)


@router.get("platforms/{platform_id}/games", response={200: PlatformGamesOut, 404: ErrorOut})
def platform_games(request: HttpRequest, platform_id: UUID) -> PlatformGames:
    """Its games in the catalog, oldest first, and what they have in common."""
    return selectors.platform_games(get_object_or_404(Platform, pk=platform_id))


@router.patch("platforms/{platform_id}", response={200: PlatformDetailOut, **ERRORS})
def update_platform(request: HttpRequest, platform_id: UUID, payload: PlatformPatch) -> Platform:
    require_admin(current_user(request))
    platform = get_object_or_404(Platform, pk=platform_id)
    return platform_service.update_platform(platform, payload)


@router.delete("platforms/{platform_id}", response={204: None, **ERRORS})
def delete_platform(request: HttpRequest, platform_id: UUID) -> Status[None]:
    require_admin(current_user(request))
    platform_service.delete_platform(get_object_or_404(Platform, pk=platform_id))
    return Status(204, None)


@router.post("platforms/{platform_id}/icon", response={200: PlatformDetailOut, **ERRORS})
def upload_platform_icon(
    request: HttpRequest, platform_id: UUID, file: File[UploadedFile]
) -> Platform:
    require_admin(current_user(request))
    return platform_service.set_icon(get_object_or_404(Platform, pk=platform_id), file)


@router.delete("platforms/{platform_id}/icon", response={200: PlatformDetailOut, **ERRORS})
def remove_platform_icon(request: HttpRequest, platform_id: UUID) -> Platform:
    require_admin(current_user(request))
    return platform_service.remove_icon(get_object_or_404(Platform, pk=platform_id))


@router.get("editions", response=list[EditionOut])
def list_editions(request: HttpRequest, q: str = "", limit: int = 20) -> list[Edition]:
    """Edition labels in use (no entity of their own: free text with suggestions)."""
    return selectors.editions(q, max(1, min(limit, 100)))


@router.get("releases", response=list[ReleaseOut])
def search_releases(
    request: HttpRequest, q: str = "", platform: UUID | None = None
) -> QuerySet[Release]:
    """Search the shared catalog (title words or a barcode)."""
    queryset = releases()
    if platform:
        queryset = queryset.filter(platform_id=platform)
    code = gtin.normalize(q)
    if code:
        return queryset.filter(barcodes__code=code)
    for word in q.split():
        queryset = queryset.filter(Q(work__title__icontains=word) | Q(title__icontains=word))
    return queryset.distinct()[:50]


@router.post("releases", response={201: ReleaseOut, **ERRORS})
def create_release(request: HttpRequest, payload: ReleaseIn) -> Status[Release]:
    """A game no source knows, entered by hand: unreviewed until an admin approves it."""
    user = current_user(request)
    require_contributor(user)
    release = service.create_release(payload, user)
    return Status(201, releases().get(pk=release.pk))


@router.get("releases/{release_id}", response={200: ReleaseOut, 404: ErrorOut})
def get_release(request: HttpRequest, release_id: UUID) -> Release:
    return get_object_or_404(releases(), pk=release_id)


@router.patch("releases/{release_id}", response={200: ReleaseOut, **ERRORS})
def update_release(request: HttpRequest, release_id: UUID, payload: ReleasePatch) -> Release:
    release = get_object_or_404(releases(), pk=release_id)
    require_edit(current_user(request), release)
    service.update_release(release, payload)
    return releases().get(pk=release.pk)


@router.post("releases/{release_id}/cover", response={200: ReleaseOut, **ERRORS})
def upload_cover(request: HttpRequest, release_id: UUID, file: File[UploadedFile]) -> Release:
    release = get_object_or_404(releases(), pk=release_id)
    require_edit(current_user(request), release)
    service.set_cover(release, file, settings.COVER_MAX_MB)
    return releases().get(pk=release.pk)


@router.post("releases/{release_id}/barcodes", response={200: ReleaseOut, **ERRORS})
def add_barcode(request: HttpRequest, release_id: UUID, payload: BarcodeIn) -> Release:
    """Unreviewed until an admin approves it (unless an admin assigns it)."""
    user = current_user(request)
    require_contributor(user)
    release = get_object_or_404(releases(), pk=release_id)
    service.attach_barcode(release, payload.code, user, source="manual")
    return releases().get(pk=release.pk)


def works() -> QuerySet[Work]:
    return Work.objects.prefetch_related(
        "genres",
        "developers",
        "series",
        "franchises",
        "releases__platform",
        "releases__publisher",
        "releases__barcodes",
        "releases__work__genres",
        "releases__work__developers",
        "releases__work__series",
        "releases__work__franchises",
    )


@router.get("works/{work_id}", response={200: WorkOut, 404: ErrorOut})
def get_work(request: HttpRequest, work_id: UUID) -> Work:
    return get_object_or_404(works(), pk=work_id)


@router.patch("works/{work_id}", response={200: WorkOut, **ERRORS})
def update_work(request: HttpRequest, work_id: UUID, payload: WorkPatch) -> Work:
    work = get_object_or_404(Work, pk=work_id)
    require_edit(current_user(request), work)
    service.update_work(work, payload)
    return works().get(pk=work_id)


@router.post("works/{work_id}/cover", response={200: WorkOut, **ERRORS})
def upload_work_cover(request: HttpRequest, work_id: UUID, file: File[UploadedFile]) -> Work:
    """A general cover for the game (key art), shown where a release has none."""
    work = get_object_or_404(Work, pk=work_id)
    require_edit(current_user(request), work)
    service.set_work_cover(work, file, settings.COVER_MAX_MB)
    return works().get(pk=work_id)


@router.delete("works/{work_id}/cover", response={200: WorkOut, 404: ErrorOut})
def delete_work_cover(request: HttpRequest, work_id: UUID) -> Work:
    work = get_object_or_404(Work, pk=work_id)
    require_edit(current_user(request), work)
    service.remove_work_cover(work)
    return works().get(pk=work_id)


@router.get("works", response=list[WorkSummaryOut])
def search_works(
    request: HttpRequest, q: str = "", exclude: UUID | None = None
) -> list[WorkSummary]:
    """Games by title words, for picking a move/merge target."""
    queryset = Work.objects.all()
    for word in q.split():
        queryset = queryset.filter(title__icontains=word)
    if exclude is not None:
        queryset = queryset.exclude(pk=exclude)
    return selectors.summaries(queryset.order_by("title")[:20])


@router.post("releases/{release_id}/move", response={200: ReleaseOut, **ERRORS})
def move(request: HttpRequest, release_id: UUID, payload: MoveReleaseIn) -> Release:
    """Move a release to another game, or make it a game of its own (no work_id)."""
    require_admin(current_user(request))
    release = get_object_or_404(Release, pk=release_id)
    target = get_object_or_404(Work, pk=payload.work_id) if payload.work_id else None
    move_release(release, target, payload.title)
    return releases().get(pk=release_id)


@router.post("works/{work_id}/merge", response={200: WorkOut, **ERRORS})
def merge(request: HttpRequest, work_id: UUID, payload: MergeWorkIn) -> Work:
    """Merge this game into the target: all releases (and so all copies) move there."""
    require_admin(current_user(request))
    source = get_object_or_404(Work, pk=work_id)
    target = get_object_or_404(Work, pk=payload.target_id)
    merge_works(source, target)
    return works().get(pk=target.pk)


def _picture_routes(slot: Literal["image", "photo"]) -> None:
    """Upload and remove the page's logo (`image`) or photo of the device (`photo`)."""

    def upload(request: HttpRequest, platform_id: UUID, file: File[UploadedFile]) -> Platform:
        require_admin(current_user(request))
        platform = get_object_or_404(Platform, pk=platform_id)
        return platform_service.set_picture(platform, slot, file)

    def remove(request: HttpRequest, platform_id: UUID) -> Platform:
        require_admin(current_user(request))
        platform = get_object_or_404(Platform, pk=platform_id)
        return platform_service.remove_picture(platform, slot)

    for view, method in ((upload, "POST"), (remove, "DELETE")):
        router.add_api_operation(
            f"platforms/{{platform_id}}/{slot}",
            [method],
            view,
            response={200: PlatformDetailOut, **ERRORS},
            operation_id=f"{'upload' if method == 'POST' else 'remove'}_platform_{slot}",
        )


for _slot in PICTURES:
    _picture_routes(_slot)
