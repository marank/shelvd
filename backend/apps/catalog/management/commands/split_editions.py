"""Move editions out of game titles and merge the games that were split by them:

    python manage.py split_editions --dry-run

"Dave The Diver: Complete Edition" becomes a release with edition "Complete Edition";
if a game "Dave the Diver" exists, both become one game.
"""

import re
from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from ...models import Release, Work
from ...services.editions import split_edition
from ...services.merge import merge_works, retitle


def _key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())


class Command(BaseCommand):
    help = "Move editions from game titles to releases and merge duplicate games."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        merged = renamed = 0
        with transaction.atomic():
            works = list(Work.objects.order_by("title"))
            # Games without an edition in their title, by normalized title: merge targets.
            by_key = {_key(w.title): w for w in works if not split_edition(w.title)[1]}
            for work in works:
                base, edition = split_edition(work.title)
                if not edition:
                    continue
                for release in work.releases.filter(edition=""):
                    release.edition = edition
                    release.save(update_fields=["edition", "updated_at"])
                target = by_key.get(_key(base))
                if target is not None:
                    merge_works(work, target)
                    merged += 1
                    self.stdout.write(f"merged   {work.title!r} → {target.title!r}")
                else:
                    work.title = base
                    work.save(update_fields=["title", "updated_at"])
                    by_key[_key(base)] = work
                    renamed += 1
                    self.stdout.write(f"renamed  {work.title!r} (edition {edition!r})")
            # Release titles that only repeat the game plus its edition aren't needed.
            cleaned = 0
            for release in Release.objects.exclude(title="").select_related("work"):
                before = (release.title, release.edition)
                retitle(release, release.title, release.work.title)
                if (release.title, release.edition) != before:
                    release.save(update_fields=["title", "edition", "updated_at"])
                    cleaned += 1
            self.stdout.write(
                f"{merged} merged, {renamed} renamed, {cleaned} release titles cleaned."
            )
            if options["dry_run"]:
                transaction.set_rollback(True)
                self.stdout.write("Dry run: nothing saved.")
