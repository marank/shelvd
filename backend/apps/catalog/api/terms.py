"""Companies, genres and series: their lists, pages, renaming, merging and deleting.

The three behave alike, so each route exists once per kind (`/catalog/companies/<id>`,
`/catalog/genres/<id>`, `/catalog/series/<id>`). Like the whole catalog, only admins
change them.
"""

from collections.abc import Callable
from typing import Any, cast
from uuid import UUID

from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from ninja import File, Router, Status, UploadedFile
from ninja.errors import HttpError

from apps.accounts.api.auth import current_user
from apps.accounts.selectors import require_admin
from apps.core.api.errors import ErrorOut

from .. import selectors
from ..models import Company, Series
from ..schemas import MergeTermIn, TermDetailOut, TermOut, TermPatch, TermSuggestionOut
from ..selectors import MODELS, TermKind
from ..selectors.terms import Term, TermDetail
from ..services import terms as service

router = Router(tags=["catalog"])

ERRORS = {400: ErrorOut, 404: ErrorOut, 409: ErrorOut}


def _register(kind: TermKind) -> None:
    model = MODELS[kind]

    def get(term_id: UUID) -> Term:
        return cast(Term, get_object_or_404(model, pk=term_id))

    def suggestions(request: HttpRequest, q: str = "", limit: int = 20) -> QuerySet[Term]:
        """Matches of `q` (all if empty), best first, with how often each is used. The
        pickers ask for a few at a time, the overview page for all (≤ 1000)."""
        return selectors.search_terms(kind, q, max(1, min(limit, 1000)))

    def detail(request: HttpRequest, term_id: UUID) -> TermDetail:
        return selectors.term_detail(get(term_id))

    def update(request: HttpRequest, term_id: UUID, payload: TermPatch) -> TermDetail:
        """Name (409 if another entry has it – merge instead), descriptions by language
        and, for a company, its details, for a series its franchise."""
        require_admin(current_user(request))
        term = get(term_id)
        if payload.company is not None:
            if not isinstance(term, Company):
                raise HttpError(400, _("Only companies have these details."))
            service.set_company_details(term, payload.company)
        if payload.series is not None:
            if not isinstance(term, Series):
                raise HttpError(400, _("Only series belong to a franchise."))
            service.set_series_details(term, payload.series)
        term = service.update(term, payload.name, payload.descriptions)
        return selectors.term_detail(term)

    def upload_image(request: HttpRequest, term_id: UUID, file: File[UploadedFile]) -> TermDetail:
        """A logo or picture: SVG (no scripts or links), JPEG, PNG or WebP, ≤ 2 MB."""
        require_admin(current_user(request))
        return selectors.term_detail(service.set_image(get(term_id), file))

    def remove_image(request: HttpRequest, term_id: UUID) -> TermDetail:
        require_admin(current_user(request))
        return selectors.term_detail(service.remove_image(get(term_id)))

    def merge(request: HttpRequest, term_id: UUID, payload: MergeTermIn) -> Term:
        """Merge this entry into the target: every game (and release) using it moves
        there, then this one is deleted."""
        require_admin(current_user(request))
        return service.merge(get(term_id), get(payload.target_id))

    def delete(request: HttpRequest, term_id: UUID) -> Status[None]:
        """Remove the entry; games and releases just lose it."""
        require_admin(current_user(request))
        service.delete(get(term_id))
        return Status(204, None)

    routes: list[tuple[Callable[..., Any], str, str, dict[str, Any]]] = [
        (suggestions, "GET", "", {"response": list[TermSuggestionOut]}),
        (detail, "GET", "/{term_id}", {"response": {200: TermDetailOut, 404: ErrorOut}}),
        (update, "PATCH", "/{term_id}", {"response": {200: TermDetailOut, **ERRORS}}),
        (upload_image, "POST", "/{term_id}/image", {"response": {200: TermDetailOut, **ERRORS}}),
        (remove_image, "DELETE", "/{term_id}/image", {"response": {200: TermDetailOut, **ERRORS}}),
        (merge, "POST", "/{term_id}/merge", {"response": {200: TermOut, **ERRORS}}),
        (delete, "DELETE", "/{term_id}", {"response": {204: None, 404: ErrorOut}}),
    ]
    for view, method, path, options in routes:
        router.add_api_operation(
            f"{kind}{path}",
            [method],
            view,
            operation_id=f"{view.__name__}_{kind}",
            **options,
        )


for _kind in MODELS:
    _register(_kind)
