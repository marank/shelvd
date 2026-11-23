"""Periodic jobs of integrations: what's due, run it, remember when it ran."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import timedelta

from django.utils import timezone

from ..models import Integration
from . import facts
from .integrations import config

logger = logging.getLogger(__name__)

# Periodic jobs of add-ons, each returning {key: things done} (see backend/addons).
Job = Callable[[], dict[str, int]]
JOBS: list[Job] = []


def register(job: Job) -> None:
    """An add-on's periodic job (AppConfig.ready); it decides itself what's due."""
    if job not in JOBS:
        JOBS.append(job)


def run_due() -> dict[str, int]:
    """Runs every periodic job whose interval has passed; returns {key: games refreshed}."""
    done: dict[str, int] = {}
    now = timezone.now()
    for key in facts.FACT_SOURCES:
        cfg = config(key)
        if not cfg.active or not cfg.options.get("periodic"):
            continue
        interval = timedelta(hours=int(cfg.options.get("periodic_hours") or 24))
        last = cfg.row.last_run_at if cfg.row else None
        if last is not None and now - last < interval:
            continue
        done[key] = facts.refresh_batch(key, int(cfg.options.get("batch") or 20))
        Integration.objects.filter(key=key).update(last_run_at=now)
        logger.info("scheduler: %s refreshed %d games", key, done[key])
    for job in JOBS:
        done.update(job())
    return done
