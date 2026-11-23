"""Descriptions of companies, series and platforms from a source (mounted under /catalog):
`/catalog/companies/<id>/description/<source>/candidates` and the same for series and
platforms, and the pictures of the entries they're linked to
(`/catalog/companies/<id>/images`)."""

from collections.abc import Callable
from typing import Any, cast
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Router

from apps.accounts.api.auth import current_user
from apps.accounts.selectors import require_admin
from apps.core.api.errors import ErrorOut

from ..schemas.descriptions import (
    DescriptionApplyIn,
    DescriptionApplyOut,
    DescriptionCandidateOut,
    ImageCandidateOut,
    ImageTakeIn,
    ImageTakenOut,
)
from ..services import descriptions
from ..services.descriptions import Term

router = Router(tags=["descriptions"])
ERRORS = {400: ErrorOut, 404: ErrorOut, 502: ErrorOut}


def _register(kind: str) -> None:
    model = descriptions.KINDS[kind]

    def description_candidates(
        request: HttpRequest, term_id: UUID, source: str, q: str = ""
    ) -> list[DescriptionCandidateOut]:
        """Entries that may describe it, the likeliest kind of thing first."""
        require_admin(current_user(request))
        term = cast(Term, get_object_or_404(model, pk=term_id))
        return [
            DescriptionCandidateOut(
                external_id=r.external_id,
                title=r.title,
                label=r.label,
                text=r.text,
                language=r.language,
                confident=r.confident,
                has_image=bool(r.image_url),
            )
            for r in descriptions.candidates(kind, term, source, q)
        ]

    def apply_description(
        request: HttpRequest, term_id: UUID, source: str, payload: DescriptionApplyIn
    ) -> DescriptionApplyOut:
        """Take the entry's text as the description (replacing the old one) and, with
        `image`, its logo as the picture."""
        require_admin(current_user(request))
        term = cast(Term, get_object_or_404(model, pk=term_id))
        applied = descriptions.apply(term, source, payload.external_id, payload.image)
        return DescriptionApplyOut(description=applied.description, image=applied.image)

    def image_candidates(request: HttpRequest, term_id: UUID) -> list[ImageCandidateOut]:
        """The pictures the entries it's linked to offer (every logo …)."""
        require_admin(current_user(request))
        term = cast(Term, get_object_or_404(model, pk=term_id))
        return [
            ImageCandidateOut.model_validate(
                {"source": c.source, "label": c.label, "kind": c.kind, "token": c.token}
            )
            for c in descriptions.images(term)
        ]

    def take_image(request: HttpRequest, term_id: UUID, payload: ImageTakeIn) -> ImageTakenOut:
        """Make one of them the picture – or a platform's photo or badge icon (`target`
        "photo", "icon")."""
        require_admin(current_user(request))
        term = cast(Term, get_object_or_404(model, pk=term_id))
        term = descriptions.take_image(term, payload.token, payload.target)
        icon, photo = getattr(term, "icon_image", None), getattr(term, "photo", None)
        return ImageTakenOut(
            image_url=term.image.url if term.image else None,
            photo_url=photo.url if photo else None,
            icon_url=icon.url if icon else None,
        )

    routes: list[tuple[Callable[..., Any], str, str, dict[str, Any]]] = [
        (
            description_candidates,
            "GET",
            "/description/{source}/candidates",
            {"response": {200: list[DescriptionCandidateOut], **ERRORS}},
        ),
        (
            apply_description,
            "POST",
            "/description/{source}",
            {"response": {200: DescriptionApplyOut, **ERRORS}},
        ),
        (
            image_candidates,
            "GET",
            "/images",
            {"response": {200: list[ImageCandidateOut], **ERRORS}},
        ),
        (take_image, "POST", "/images", {"response": {200: ImageTakenOut, **ERRORS}}),
    ]
    for view, method, path, options in routes:
        router.add_api_operation(
            f"{kind}/{{term_id}}{path}",
            [method],
            view,
            operation_id=f"{view.__name__}_{kind}",
            **options,
        )


for _kind in descriptions.KINDS:
    _register(_kind)


@router.get("term-image-preview", response={200: None, **ERRORS})
def term_image_preview(request: HttpRequest, token: str) -> HttpResponse:
    """A picture to choose, through the server (the browser never sees the URL)."""
    require_admin(current_user(request))
    content, content_type = descriptions.image(token)
    response = HttpResponse(content, content_type=content_type)
    response["Cache-Control"] = "private, max-age=3600"
    # An SVG opened on its own must not run anything (it's checked, but still).
    response["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
    return response


@router.get("commons-images", response={200: list[ImageCandidateOut], **ERRORS})
def commons_images(request: HttpRequest, q: str = "") -> list[ImageCandidateOut]:
    """Pictures on Wikimedia Commons for a query – to take one as a picture, photo or icon
    (`POST …/images` with its token)."""
    require_admin(current_user(request))
    return [
        ImageCandidateOut.model_validate(
            {"source": c.source, "label": c.label, "kind": c.kind, "token": c.token}
        )
        for c in descriptions.search_images(q)
    ]
