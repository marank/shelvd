"""Moving releases between games and merging games.

Copies hang on releases, so they move along; nothing in a library changes.
"""

from __future__ import annotations

import re

from django.db import transaction
from django.utils.translation import gettext as _
from ninja.errors import HttpError

from ..models import Release, Work
from ..signals import work_merged
from .editions import split_edition


def _same(a: str, b: str) -> bool:
    return re.sub(r"[^a-z0-9]+", "", a.lower()) == re.sub(r"[^a-z0-9]+", "", b.lower())


def retitle(release: Release, old_title: str, new_title: str) -> None:
    """After a move: an edition in the old title goes to the edition field; the old
    title stays as the release's own title only if it really differs."""
    title = release.title or old_title
    base, edition = split_edition(title)
    if edition and (not release.edition or _same(edition, release.edition)):
        release.edition = release.edition or edition
        title = base
    release.title = "" if _same(title, new_title) else title


def _fill(target: Work, source: Work, *, cover: bool) -> None:
    """Give the target what it lacks from the source (never overwrite). The cover's file
    moves over only if the source goes away (`cover`): a shared file would be deleted
    with either game's cover."""
    changed = []
    for name in ("summary", "first_release_date"):
        if not getattr(target, name) and getattr(source, name):
            setattr(target, name, getattr(source, name))
            changed.append(name)
    if cover and not target.cover and source.cover:
        target.cover = source.cover  # the file moves over (no copy)
        changed += ["cover", "cover_width", "cover_height"]
    if changed:
        target.save(update_fields=[*changed, "updated_at"])
    if not target.series.exists():
        target.series.set(source.series.all())
    if not target.franchises.exists():
        target.franchises.set(source.franchises.all())
    if not target.genres.exists():
        target.genres.set(source.genres.all())
    if not target.developers.exists():
        target.developers.set(source.developers.all())


def _move_links(source: Work, target: Work) -> None:
    """What others keep about the game that's going away follows it (see signals)."""
    work_merged.send(sender=Work, source=source, target=target)


@transaction.atomic
def move_release(release: Release, target: Work | None, title: str = "") -> Work:
    """Move a release to another game, or (target None) make it a game of its own."""
    source = release.work
    if target is not None and target.pk == source.pk:
        raise HttpError(400, _("The release already belongs to this game."))
    if target is None:
        target = Work.objects.create(
            title=title.strip() or release.display_title,
            media_type=source.media_type,
            summary=source.summary,
            first_release_date=release.release_date or source.first_release_date,
        )
        target.genres.set(source.genres.all())
        target.developers.set(source.developers.all())
        target.series.set(source.series.all())
        target.franchises.set(source.franchises.all())
    else:
        _fill(target, source, cover=not source.releases.exclude(pk=release.pk).exists())
    retitle(release, source.title, target.title)
    release.work = target
    release.save()
    if not source.releases.exists():
        _move_links(source, target)
        source.delete()
    return target


@transaction.atomic
def merge_works(source: Work, target: Work) -> Work:
    """All releases of `source` become releases of `target`; `source` is deleted."""
    if source.pk == target.pk:
        raise HttpError(400, _("A game can't be merged into itself."))
    _fill(target, source, cover=True)
    for release in source.releases.all():
        retitle(release, source.title, target.title)
        release.work = target
        release.save()
    _move_links(source, target)
    source.delete()
    return target
