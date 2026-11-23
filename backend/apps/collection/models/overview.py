from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

from .choices import Layout


class Overview(TimeStampedModel):
    """A saved view of a library: nesting (e.g. platform › publisher › year), filters, layout.

    Personal per user, so viewers of a shared library can build their own.
    """

    library = models.ForeignKey(
        "collection.Library", on_delete=models.CASCADE, related_name="overviews"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="overviews"
    )
    name = models.CharField(max_length=200)
    group_by = models.JSONField(default=list, blank=True)  # selectors.grouping.FIELDS keys
    # One grouping field whose groups get collapsible headings in the item list
    # ("" = none); unlike group_by it doesn't make folders.
    section = models.CharField(max_length=40, blank=True, default="")
    # Filter conditions in the syntax of selectors.conditions, for example game.kind=game,
    # game.title~A* or location.box? – `match` says whether all of them must hold or any one.
    filters = models.JSONField(default=list, blank=True)
    match = models.CharField(max_length=3, default="all")
    # Fields shown per presentation: {"grid"|"list"|"table"|"detail": [field keys]}, keys of
    # the frontend's field registry. A missing or empty list = that presentation's defaults.
    fields = models.JSONField(default=dict, blank=True)
    # Comma-separated levels, "-" for descending: "location.box,-release.number"
    # (selectors.sorting).
    sort = models.CharField(max_length=300, default="game.title")
    layout = models.CharField(max_length=10, choices=Layout.choices, default=Layout.GRID)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "name"]
        verbose_name = _("overview")
        verbose_name_plural = _("overviews")

    def __str__(self) -> str:
        return self.name
