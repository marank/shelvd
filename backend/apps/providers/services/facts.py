"""Play times, critic scores … per game from facts sources, cached in catalog.WorkFact.

A fact is refreshed when it's older than its source's max age: when someone opens the
game (`refresh_work`), by the scheduler (`refresh_batch`), or on request (`force`). If a
source fails, the cached values stay and the error is shown on the integrations page.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import timedelta
from difflib import SequenceMatcher

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _
from ninja.errors import HttpError

from apps.catalog.models import MediaType, Work, WorkFact
from apps.catalog.services.editions import split_edition

from ..sources.base import FactRecord, FactSource, ProviderError
from ..sources.registry import fact_source
from .covers import search_titles
from .integrations import config, record_error, record_ok

FACT_SOURCES = ("hltb", "opencritic")


# "Dr Kawashima's Brain Training for Nintendo Switch": the platform isn't part of the name.
FOR_PLATFORM = re.compile(r"\s+(?:for\s+)?nintendo\s+switch(?:\s+edition)?$", re.IGNORECASE)
# Any "<word> Edition" at the end ("Darksiders Warmastered Edition").
ANY_EDITION = re.compile(r"[\s:–-]+[\w'\u2019]+\s+edition$", re.IGNORECASE)
# "Pokémon Black Version 2" is "Pokémon Black 2" elsewhere.
VERSION = re.compile(r"\s+version(?=\s+\d+$|$)", re.IGNORECASE)
# "Horizon: Zero Dawn" is "Horizon Zero Dawn" elsewhere.
PUNCTUATION = re.compile(r"\s*(?::|\s[-–]\s)\s*")
# "Pokémon X and Y": both games under one entry.
PAIR = re.compile(r"^(?P<first>.+?)\s+(?:and|&)\s+(?P<second>[^&]+)$", re.IGNORECASE)
# "ATOMIK: RunGunJumpGun", "Agatha Christie - Murder on the Orient Express".
SUBTITLE = re.compile(r"^.+?(?::|\s[-–]\s)\s*(?P<rest>.+)$")


def normalize_title(title: str) -> str:
    base, _edition = split_edition(FOR_PLATFORM.sub("", title))
    plain = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", plain.lower())


def title_forms(title: str) -> list[str]:
    """A source's title and, for a pair ("Pokémon Omega Ruby and Alpha Sapphire"), each
    game of it ("Pokémon Omega Ruby", "Pokémon Alpha Sapphire")."""
    forms = [title]
    if pair := PAIR.match(title):
        first, second = pair["first"].split(), pair["second"].split()
        if len(first) > len(second):
            forms += [" ".join(first), " ".join(first[: -len(second)] + second)]
    return forms


def fact_titles(title: str) -> list[tuple[str, bool]]:
    """What to search for, in order, and whether only an exact hit counts: the title, the
    title without edition words or "Version", without ":" and " - ", then its subtitle alone
    (exact only – a subtitle is short and often generic)."""
    tries = [(t, False) for t in search_titles(title)]
    tries.extend(
        (shorter, False)
        for shorter in (ANY_EDITION.sub("", title.strip()), VERSION.sub("", title.strip()))
        if shorter != title.strip()
    )
    shortest = min((t for t, _exact in tries), key=len)
    if (spaced := PUNCTUATION.sub(" ", shortest)) != shortest:
        tries.append((spaced, False))
    if (subtitle := SUBTITLE.match(shortest)) and len(subtitle["rest"]) >= 4:
        tries.append((subtitle["rest"], True))
    unique: dict[str, bool] = {}
    for query, exact in tries:
        unique.setdefault(query, exact)
    return list(unique.items())


def find(source: FactSource, title: str) -> FactRecord | None:
    """The best record for a game's title, trying shorter forms when nothing matches."""
    for query, exact in fact_titles(title):
        record = best_match(query, source.search(query), exact=exact)
        if record is not None:
            return record
    return None


def best_match(title: str, records: list[FactRecord], *, exact: bool = False) -> FactRecord | None:
    """The record with the same title, else (unless `exact`) a very similar one, else none."""
    wanted = normalize_title(title)
    # One game of a pair counts only when it's exactly that game ("Pokémon Y" in "Pokémon X
    # and Y"), never as "similar" ("Pokémon White 2" ≠ "… Volt White 2").
    scored = [
        (
            1.0
            if wanted in {normalize_title(f) for f in title_forms(r.title)}
            else SequenceMatcher(None, wanted, normalize_title(r.title)).ratio(),
            r,
        )
        for r in records
    ]
    same = [r for score, r in scored if score == 1]
    if same:
        return same[0]
    if exact:
        return None
    score, record = max(scored, key=lambda pair: pair[0], default=(0.0, None))
    return record if score >= 0.85 else None


def max_age(key: str) -> timedelta:
    return timedelta(hours=int(config(key).options.get("max_age_hours") or 720))


def is_stale(fact: WorkFact | None, key: str) -> bool:
    return (
        fact is None or fact.fetched_at is None or fact.fetched_at < timezone.now() - max_age(key)
    )


def refresh(work: Work, key: str, *, force: bool = False) -> WorkFact | None:
    fact = WorkFact.objects.filter(work=work, source=key).first()
    source = fact_source(key)
    # Play times and scores are for games, not figures.
    if source is None or work.media_type != MediaType.GAME or not (force or is_stale(fact, key)):
        return fact
    try:
        if fact and fact.pinned and fact.external_id:
            record = source.get(fact.external_id)
        else:
            record = find(source, work.title)
            if record is not None and not record.values:
                record = source.get(record.external_id) or record
        record_ok(key)
    except ProviderError as exc:
        record_error(key, str(exc))
        return fact
    fact = fact or WorkFact(work=work, source=key)
    if record is None:
        fact.status = WorkFact.Status.MISSING
        fact.values = {}
        fact.external_id = fact.title = fact.url = ""
    else:
        fact.status = WorkFact.Status.OK
        fact.external_id = record.external_id
        fact.title = record.title
        fact.url = record.url
        fact.values = record.values
    fact.fetched_at = timezone.now()
    fact.save()
    return fact


def refresh_work(work: Work) -> bool:
    """Opening a game: refresh whatever is stale. True if anything was fetched."""
    before = {f.source: f.fetched_at for f in WorkFact.objects.filter(work=work)}
    changed = False
    for key in FACT_SOURCES:
        fact = refresh(work, key)
        changed |= fact is not None and fact.fetched_at != before.get(key)
    return changed


def refresh_batch(key: str, limit: int) -> int:
    """The scheduler's job: the games that were never fetched or are stalest first."""
    if fact_source(key) is None:
        return 0
    cutoff = timezone.now() - max_age(key)
    due = (
        Work.objects.filter(media_type=MediaType.GAME)
        .filter(~Q(facts__source=key) | Q(facts__source=key, facts__fetched_at__lt=cutoff))
        .distinct()
        .order_by("title")[:limit]
    )
    return sum(1 for work in due if refresh(work, key) is not None)


def candidates(work: Work, key: str, query: str = "") -> list[FactRecord]:
    source = fact_source(key)
    if source is None:
        raise HttpError(400, _("This integration is switched off."))
    try:
        found = source.search(query.strip() or work.title)
    except ProviderError as exc:
        record_error(key, str(exc))
        raise HttpError(502, str(exc)) from exc
    return found


def pin(work: Work, key: str, external_id: str) -> WorkFact:
    """A person chose the matching entry; keep it from now on."""
    source = fact_source(key)
    if source is None:
        raise HttpError(400, _("This integration is switched off."))
    try:
        record = source.get(external_id)
    except ProviderError as exc:
        record_error(key, str(exc))
        raise HttpError(502, str(exc)) from exc
    if record is None:
        raise HttpError(404, _("The source doesn't know this entry."))
    fact, _created = WorkFact.objects.update_or_create(
        work=work,
        source=key,
        defaults={
            "external_id": record.external_id,
            "title": record.title,
            "url": record.url,
            "values": record.values,
            "status": WorkFact.Status.OK,
            "pinned": True,
            "fetched_at": timezone.now(),
        },
    )
    return fact


def unpin(work: Work, key: str) -> None:
    """Forget the choice: the next refresh searches again."""
    WorkFact.objects.filter(work=work, source=key).delete()
