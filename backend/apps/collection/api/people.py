from uuid import UUID

from django.db.models import Count, Q
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from ninja import Router, Status
from ninja.errors import HttpError

from apps.accounts.api.auth import current_user
from apps.core.api.errors import ErrorOut

from ..models import Person
from ..schemas import PersonIn, PersonOut, PersonPatch
from ..services.access import get_library
from ..services.visibility import visibility

router = Router(tags=["people"])
ERRORS = {400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 409: ErrorOut}


def person_out(person: Person) -> PersonOut:
    return PersonOut(
        id=person.pk,
        name=person.name,
        email=person.email,
        notes=person.notes,
        open_loans=getattr(person, "open_loans", 0),
    )


@router.get("{library_id}/people", response={200: list[PersonOut], **ERRORS})
def list_people(request: HttpRequest, library_id: UUID) -> list[PersonOut]:
    user = current_user(request)
    library = get_library(user, library_id)
    people = library.people.annotate(
        open_loans=Count("loans", filter=Q(loans__returned_on__isnull=True))
    )
    if visibility(library, user).full:
        return [person_out(p) for p in people]
    # Viewers: names only (who owns a copy), no contact details or loans.
    return [PersonOut(id=p.pk, name=p.name, email="", notes="") for p in people]


@router.post("{library_id}/people", response={201: PersonOut, **ERRORS})
def create_person(request: HttpRequest, library_id: UUID, payload: PersonIn) -> Status[PersonOut]:
    library = get_library(current_user(request), library_id, need="editor")
    if not payload.name.strip():
        raise HttpError(400, _("A name is required."))
    person = Person.objects.create(
        library=library, name=payload.name.strip(), email=payload.email, notes=payload.notes
    )
    return Status(201, person_out(person))


@router.patch("{library_id}/people/{person_id}", response={200: PersonOut, **ERRORS})
def update_person(
    request: HttpRequest, library_id: UUID, person_id: UUID, payload: PersonPatch
) -> PersonOut:
    library = get_library(current_user(request), library_id, need="editor")
    person = get_object_or_404(Person, pk=person_id, library=library)
    for name, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(person, name, value)
    person.save()
    return person_out(person)


@router.delete("{library_id}/people/{person_id}", response={204: None, **ERRORS})
def delete_person(request: HttpRequest, library_id: UUID, person_id: UUID) -> Status[None]:
    library = get_library(current_user(request), library_id, need="editor")
    person = get_object_or_404(Person, pk=person_id, library=library)
    if person.loans.exists():
        raise HttpError(409, _("This person has loans; they stay in the history."))
    person.delete()
    return Status(204, None)
