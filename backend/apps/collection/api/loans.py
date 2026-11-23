from uuid import UUID

from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Status

from apps.accounts.api.auth import current_user
from apps.core.api.errors import ErrorOut

from ..models import Library, Loan
from ..schemas import LoanIn, LoanOut, LoanReturnIn
from ..services import loans as service
from ..services.access import get_library

router = Router(tags=["loans"])
ERRORS = {400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 409: ErrorOut}


def loans(library: Library) -> QuerySet[Loan]:
    return Loan.objects.filter(item__library=library).select_related(
        "borrower", "item__release__work", "item__release__platform"
    )


@router.get("{library_id}/loans", response={200: list[LoanOut], **ERRORS})
def list_loans(
    request: HttpRequest, library_id: UUID, open: bool | None = None, item: UUID | None = None
) -> QuerySet[Loan]:
    # Who borrowed what is for those who look after the library.
    library = get_library(current_user(request), library_id, need="editor")
    queryset = loans(library)
    if open is not None:
        queryset = queryset.filter(returned_on__isnull=open)
    if item is not None:
        queryset = queryset.filter(item_id=item)
    return queryset


@router.post("{library_id}/loans", response={201: LoanOut, **ERRORS})
def lend(request: HttpRequest, library_id: UUID, payload: LoanIn) -> Status[Loan]:
    library = get_library(current_user(request), library_id, need="editor")
    loan = service.lend(library, payload)
    return Status(201, loans(library).get(pk=loan.pk))


@router.post("{library_id}/loans/{loan_id}/return", response={200: LoanOut, **ERRORS})
def give_back(request: HttpRequest, library_id: UUID, loan_id: UUID, payload: LoanReturnIn) -> Loan:
    library = get_library(current_user(request), library_id, need="editor")
    return service.give_back(get_object_or_404(loans(library), pk=loan_id), payload.returned_on)


@router.delete("{library_id}/loans/{loan_id}", response={204: None, **ERRORS})
def delete_loan(request: HttpRequest, library_id: UUID, loan_id: UUID) -> Status[None]:
    library = get_library(current_user(request), library_id, need="editor")
    get_object_or_404(loans(library), pk=loan_id).delete()
    return Status(204, None)
