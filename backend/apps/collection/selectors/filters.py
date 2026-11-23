from django.utils.translation import gettext as _
from ninja.errors import HttpError

from .grouping import FIELDS


def check_fields(keys: list[str]) -> list[str]:
    unknown = [key for key in keys if key not in FIELDS]
    if unknown:
        raise HttpError(400, _("Unknown field: %(field)s") % {"field": ", ".join(unknown)})
    return keys


def parse_filters(raw: list[str]) -> dict[str, list[str]]:
    """["platform:<uuid>", "year:2004", "genre:a", "genre:b"] → {field: [keys]}."""
    filters: dict[str, list[str]] = {}
    for entry in raw:
        field, sep, key = entry.partition(":")
        if not sep:
            raise HttpError(400, _("Filters look like field:value."))
        filters.setdefault(field, []).append(key)
    check_fields(list(filters))
    return filters
