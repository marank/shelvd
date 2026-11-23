"""Barcode lookup in our own catalog and title search across the configured sources."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from django.utils.translation import get_language

from apps.catalog.models import Barcode, Platform, Release

from ..sources import GameRecord, ProviderError, metadata_sources
from . import gtin as gtin_utils

logger = logging.getLogger(__name__)


@dataclass
class Candidate:
    record: GameRecord
    platform: Platform | None


@dataclass
class SearchResult:
    query: str
    platform: Platform | None
    candidates: list[Candidate] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class BarcodeResult:
    code: str
    known: list[Release] = field(default_factory=list)


def search(query: str, platform: Platform | None = None) -> SearchResult:
    result = SearchResult(query=query, platform=platform)
    known_platforms = {
        str(external_id): p
        for p in Platform.objects.all()
        for name, external_id in p.external_ids.items()
        if name == "igdb"
    }
    for source in metadata_sources(catalog=True):
        platform_id = platform.external_ids.get(source.name) if platform else None
        try:
            records = source.search(
                query, str(platform_id) if platform_id else None, language=get_language()
            )
        except ProviderError as exc:
            logger.warning("%s", exc)
            result.errors.append(source.name)
            continue
        for record in records:
            mapped = known_platforms.get(record.platform_external_id or "")
            # Platforms we don't track (arcade, mobile, …) are just noise in the picker.
            if mapped is not None:
                result.candidates.append(Candidate(record=record, platform=mapped))
    return result


def lookup_barcode(code: str) -> BarcodeResult:
    """What our own data knows: confirmed barcodes, and for an article number (no GTIN)
    also a release's product code. No outside source maps game barcodes reliably, so an
    unknown code goes to the title search and is remembered once confirmed."""
    result = BarcodeResult(code=code)
    known = Barcode.objects.filter(code=code).select_related("release")
    result.known = [barcode.release for barcode in known]
    if not gtin_utils.is_gtin(code):
        by_product = Release.objects.filter(product_code__iexact=code).exclude(
            pk__in=[r.pk for r in result.known]
        )
        result.known += list(by_product.order_by("pk"))
    return result
