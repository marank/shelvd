from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class Loan(TimeStampedModel):
    """An item lent to a person; open while returned_on is empty."""

    item = models.ForeignKey("collection.Item", on_delete=models.CASCADE, related_name="loans")
    # RESTRICT, not PROTECT: a person with loans can't be deleted on their own, but
    # deleting the whole library takes the loans (via the items) and people along.
    borrower = models.ForeignKey(
        "collection.Person", on_delete=models.RESTRICT, related_name="loans"
    )
    lent_on = models.DateField()
    due_on = models.DateField(null=True, blank=True)
    returned_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-lent_on", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["item"],
                condition=models.Q(returned_on__isnull=True),
                name="one_open_loan_per_item",
            )
        ]
        verbose_name = _("loan")
        verbose_name_plural = _("loans")

    def __str__(self) -> str:
        return f"{self.item} → {self.borrower}"
