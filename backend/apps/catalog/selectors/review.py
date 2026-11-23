"""The admins' review queue: what people entered themselves and nobody has checked yet;
and who may still change such an entry."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.db.models import Count

from apps.accounts.models import User
from apps.accounts.selectors import is_admin

from ..models import Barcode, Release, ReviewStatus, Work


@dataclass
class ReviewEntry:
    kind: str
    id: UUID
    title: str
    detail: str
    work_id: UUID
    release_id: UUID | None
    created_by: str | None
    created_at: datetime
    copies: int


def can_edit(user: User, entry: Work | Release) -> bool:
    """Admins; and the creator of an entry that is still unreviewed (to fix typos)."""
    return is_admin(user) or (entry.pending and entry.created_by_id == user.pk)


def _release_detail(release: Release) -> str:
    parts = [release.platform.name, release.get_region_display(), release.edition]
    return " · ".join(str(p) for p in parts if p)


def pending_count() -> int:
    pending = ReviewStatus.PENDING
    return (
        Work.objects.filter(review_status=pending).count()
        + Release.objects.filter(review_status=pending).count()
        + Barcode.objects.filter(review_status=pending).count()
    )


def review_queue() -> list[ReviewEntry]:
    """Oldest first. A game shows up on its own only when none of its releases waits too
    (approving a release approves its game)."""
    pending = ReviewStatus.PENDING
    releases = (
        Release.objects.filter(review_status=pending)
        .select_related("work", "platform", "created_by")
        .annotate(copies=Count("items"))
    )
    entries = [
        ReviewEntry(
            "release",
            r.pk,
            r.display_title,
            _release_detail(r),
            r.work_id,
            r.pk,
            r.created_by.username if r.created_by else None,
            r.created_at,
            r.copies,
        )
        for r in releases
    ]
    works = (
        Work.objects.filter(review_status=pending)
        .exclude(releases__review_status=pending)
        .select_related("created_by")
        .annotate(copies=Count("releases__items"))
    )
    entries.extend(
        ReviewEntry(
            "work",
            w.pk,
            w.title,
            "",
            w.pk,
            None,
            w.created_by.username if w.created_by else None,
            w.created_at,
            w.copies,
        )
        for w in works
    )
    barcodes = (
        Barcode.objects.filter(review_status=pending)
        .select_related("release__work", "release__platform", "confirmed_by")
        .annotate(copies=Count("release__items"))
    )
    entries.extend(
        ReviewEntry(
            "barcode",
            b.pk,
            b.release.display_title,
            f"{b.code} → {_release_detail(b.release)}",
            b.release.work_id,
            b.release_id,
            b.confirmed_by.username if b.confirmed_by else None,
            b.created_at,
            b.copies,
        )
        for b in barcodes
    )
    return sorted(entries, key=lambda e: e.created_at)
