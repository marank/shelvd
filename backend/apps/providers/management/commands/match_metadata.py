"""Matches every game of the catalog with a metadata source and fills in what's missing.

python manage.py match_metadata            # dry run: what would change
python manage.py match_metadata --apply    # take it

The source's answers are kept under DATA_DIR/answers/<source>, so the dry run and the real
one ask IGDB only once; --fresh asks again.
"""

from __future__ import annotations

import shutil
from argparse import ArgumentParser
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.catalog.models import Work

from ...services.bulk_match import Outcome, run
from ...services.metadata import Change, Value
from ...sources import metadata_source
from ...sources.igdb import saved_answers


def _value(value: Value) -> str:
    if value.date:
        return value.date.isoformat() + (f" ({value.precision})" if value.precision else "")
    if value.image:
        return "image"
    text = " ".join(value.text.split())
    return text if len(text) <= 70 else text[:67] + "…"


def _change(change: Change) -> str:
    where = (
        f"{change.release.platform.short_name or change.release.platform.name} "
        if change.release
        else ""
    )
    return f"{where}{change.field}: {_value(change.current) or '–'} → {_value(change.proposed)}"


class Command(BaseCommand):
    help = "Match the catalog's games with a metadata source and fill in what's missing."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--source", default="igdb")
        parser.add_argument("--apply", action="store_true", help="Write the changes.")
        parser.add_argument("--fresh", action="store_true", help="Ask the source again.")
        parser.add_argument("--work", action="append", default=[], help="Only this work id.")

    def handle(self, *args: Any, **options: Any) -> None:
        key = str(options["source"])
        if metadata_source(key) is None:
            raise CommandError(f"The integration {key!r} is switched off or unknown.")
        answers = settings.DATA_DIR / "answers" / key
        if options["fresh"]:
            shutil.rmtree(answers, ignore_errors=True)
        works = list(Work.objects.filter(pk__in=options["work"])) if options["work"] else None
        with saved_answers(answers):
            outcomes = run(key, bool(options["apply"]), works)
        self.report(outcomes, bool(options["apply"]))

    def report(self, outcomes: list[Outcome], applied: bool) -> None:
        out = self.stdout.write
        for outcome in outcomes:
            head = f"[{outcome.status}] {outcome.work.title}"
            if outcome.record:
                head += f"  ⇒  {outcome.record.title} ({outcome.record.external_id})"
            out(head + (f"  – {outcome.note}" if outcome.note else ""))
            for change in outcome.taken:
                out(f"    + {_change(change)}")
            for change in outcome.left:
                out(f"    · {_change(change)}")
        counts: dict[str, int] = {}
        for outcome in outcomes:
            counts[outcome.status] = counts.get(outcome.status, 0) + 1
        taken = sum(len(o.taken) for o in outcomes)
        out("")
        out(", ".join(f"{n} {status}" for status, n in sorted(counts.items())))
        out(f"{taken} changes {'applied' if applied else 'would be applied'} (+); · = left as is")
