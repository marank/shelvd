from datetime import date

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from ninja.errors import HttpError

from ..models import Item, Library, Loan, Person
from ..schemas import LoanIn


@transaction.atomic
def lend(library: Library, data: LoanIn) -> Loan:
    item = Item.objects.filter(pk=data.item_id, library=library).first()
    if item is None:
        raise HttpError(400, _("Unknown item."))
    if data.borrower_id:
        borrower = Person.objects.filter(pk=data.borrower_id, library=library).first()
        if borrower is None:
            raise HttpError(400, _("Unknown person."))
    elif data.borrower_name.strip():
        borrower, _created = Person.objects.get_or_create(
            library=library, name=data.borrower_name.strip()
        )
    else:
        raise HttpError(400, _("Who borrows it?"))
    try:
        with transaction.atomic():
            return Loan.objects.create(
                item=item,
                borrower=borrower,
                lent_on=data.lent_on or timezone.localdate(),
                due_on=data.due_on,
                notes=data.notes,
            )
    except IntegrityError as exc:
        raise HttpError(409, _("This item is already lent out.")) from exc


def give_back(loan: Loan, returned_on: date | None) -> Loan:
    if loan.returned_on is not None:
        raise HttpError(409, _("This loan is already closed."))
    loan.returned_on = returned_on or timezone.localdate()
    loan.save(update_fields=["returned_on", "updated_at"])
    return loan
