from uuid import UUID

from django.db.models import Count, QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from ninja import Router, Status
from ninja.errors import HttpError

from apps.accounts.api.auth import current_user
from apps.accounts.models import User
from apps.core.api.errors import ErrorOut

from ..models import Library, LibraryMember, Role, ViewerLoans
from ..schemas import LibraryIn, LibraryOut, LibraryPatch, MemberIn, MemberOut, MemberPatch
from ..services import libraries as service
from ..services.access import get_library, role_in, visible_libraries

router = Router(tags=["libraries"])
ERRORS = {400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 409: ErrorOut}


def library_out(library: Library, user: User) -> LibraryOut:
    role = role_in(library, user) or "viewer"
    count = getattr(library, "item_count", None)
    return LibraryOut(
        id=library.pk,
        name=library.name,
        description=library.description,
        owner=library.owner.get_username(),
        role=role,
        item_count=count if count is not None else library.items.count(),
        public_token=library.public_token if role == "owner" else None,
        viewer_loans=ViewerLoans(library.viewer_loans),
        created_at=library.created_at,
    )


def member_out(member: LibraryMember) -> MemberOut:
    return MemberOut(id=member.pk, username=member.user.get_username(), role=Role(member.role))


@router.get("", response=list[LibraryOut])
def list_libraries(request: HttpRequest) -> list[LibraryOut]:
    user = current_user(request)
    libraries: QuerySet[Library] = (
        visible_libraries(user)
        .select_related("owner")
        .annotate(item_count=Count("items", distinct=True))
        .order_by("name")
    )
    return [library_out(library, user) for library in libraries]


@router.post("", response={201: LibraryOut, **ERRORS})
def create_library(request: HttpRequest, payload: LibraryIn) -> Status[LibraryOut]:
    user = current_user(request)
    library = service.create_library(user, payload.name, payload.description)
    return Status(201, library_out(library, user))


@router.get("{library_id}", response={200: LibraryOut, **ERRORS})
def get_library_view(request: HttpRequest, library_id: UUID) -> LibraryOut:
    user = current_user(request)
    return library_out(get_library(user, library_id), user)


@router.patch("{library_id}", response={200: LibraryOut, **ERRORS})
def update_library(request: HttpRequest, library_id: UUID, payload: LibraryPatch) -> LibraryOut:
    user = current_user(request)
    library = get_library(user, library_id, need="owner")
    for name, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(library, name, value.strip() if name == "name" else value)
    if not library.name:
        raise HttpError(400, _("A name is required."))
    library.save()
    return library_out(library, user)


@router.delete("{library_id}", response={204: None, **ERRORS})
def delete_library(request: HttpRequest, library_id: UUID) -> Status[None]:
    service.delete_library(get_library(current_user(request), library_id, need="owner"))
    return Status(204, None)


@router.post("{library_id}/public-link", response={200: LibraryOut, **ERRORS})
def enable_public_link(request: HttpRequest, library_id: UUID) -> LibraryOut:
    user = current_user(request)
    return library_out(
        service.enable_public_link(get_library(user, library_id, need="owner")), user
    )


@router.delete("{library_id}/public-link", response={200: LibraryOut, **ERRORS})
def disable_public_link(request: HttpRequest, library_id: UUID) -> LibraryOut:
    user = current_user(request)
    library = get_library(user, library_id, need="owner")
    return library_out(service.disable_public_link(library), user)


@router.get("{library_id}/members", response={200: list[MemberOut], **ERRORS})
def list_members(request: HttpRequest, library_id: UUID) -> list[MemberOut]:
    library = get_library(current_user(request), library_id)
    return [member_out(m) for m in library.members.select_related("user")]


@router.post("{library_id}/members", response={201: MemberOut, **ERRORS})
def add_member(request: HttpRequest, library_id: UUID, payload: MemberIn) -> Status[MemberOut]:
    library = get_library(current_user(request), library_id, need="owner")
    return Status(201, member_out(service.add_member(library, payload.username, payload.role)))


@router.patch("{library_id}/members/{member_id}", response={200: MemberOut, **ERRORS})
def update_member(
    request: HttpRequest, library_id: UUID, member_id: UUID, payload: MemberPatch
) -> MemberOut:
    library = get_library(current_user(request), library_id, need="owner")
    member = get_object_or_404(
        LibraryMember.objects.select_related("user"), pk=member_id, library=library
    )
    member.role = payload.role
    member.save(update_fields=["role", "updated_at"])
    return member_out(member)


@router.delete("{library_id}/members/{member_id}", response={204: None, **ERRORS})
def remove_member(request: HttpRequest, library_id: UUID, member_id: UUID) -> Status[None]:
    user = current_user(request)
    library = get_library(user, library_id)
    member = get_object_or_404(LibraryMember, pk=member_id, library=library)
    # The owner removes anyone; members may leave on their own.
    if library.owner_id != user.pk and member.user_id != user.pk:
        get_library(user, library_id, need="owner")
    member.delete()
    return Status(204, None)
