"""Runs the integrations' periodic jobs: every minute it checks what is due.

python manage.py run_scheduler          # keeps running (supervisord in Docker)
python manage.py run_scheduler --once   # one round, e.g. from cron or by hand
"""

from __future__ import annotations

import signal
import threading
import time
from argparse import ArgumentParser
from types import FrameType
from typing import Any

from django.core.management.base import BaseCommand
from django.db import DatabaseError, close_old_connections

from ...services.scheduler import run_due

TICK = 60


class Command(BaseCommand):
    help = "Run due periodic jobs of the integrations (refreshing play times, scores …)."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--once", action="store_true", help="Run one round and exit.")

    def handle(self, *args: Any, **options: Any) -> None:
        # Set by the signal handler; only checked (never waited on) here, so the handler
        # can't block on the event's lock.
        stopping = threading.Event()

        def stop(signum: int, frame: FrameType | None) -> None:
            stopping.set()

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        while not stopping.is_set():
            close_old_connections()
            try:
                for key, count in run_due().items():
                    self.stdout.write(f"{key}: {count} games refreshed")
            except DatabaseError as exc:
                # Not migrated yet or briefly unreachable: try again next round.
                self.stderr.write(f"scheduler: database not ready ({exc})")
            if options["once"]:
                return
            for _second in range(TICK):
                if stopping.is_set():
                    break
                time.sleep(1)
