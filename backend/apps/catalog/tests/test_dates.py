from collections.abc import Callable
from datetime import date

import pytest

from apps.catalog.models import Platform, Release
from apps.catalog.models.dates import FAR_FUTURE, is_released, period, sort_date


@pytest.mark.parametrize(
    ("precision", "start", "end", "expected"),
    [
        ("day", date(2026, 3, 5), None, (date(2026, 3, 5), date(2026, 3, 5))),
        ("week", date(2026, 3, 5), None, (date(2026, 3, 2), date(2026, 3, 8))),
        ("month", date(2026, 2, 17), None, (date(2026, 2, 1), date(2026, 2, 28))),
        ("quarter", date(2026, 8, 9), None, (date(2026, 7, 1), date(2026, 9, 30))),
        ("half", date(2026, 3, 1), None, (date(2026, 1, 1), date(2026, 6, 30))),
        ("half", date(2026, 9, 1), None, (date(2026, 7, 1), date(2026, 12, 31))),
        ("year", date(2026, 5, 5), None, (date(2026, 1, 1), date(2026, 12, 31))),
        ("window", date(2026, 5, 5), date(2026, 6, 1), (date(2026, 5, 5), date(2026, 6, 1))),
        ("window", date(2026, 5, 5), date(2026, 1, 1), (date(2026, 5, 5), date(2026, 5, 5))),
        ("tba", date(2026, 5, 5), None, (None, None)),
        ("day", None, None, (None, None)),
    ],
)
def test_period(
    precision: str, start: date | None, end: date | None, expected: tuple[date | None, ...]
) -> None:
    assert period(precision, start, end) == expected


def test_sort_and_released() -> None:
    assert sort_date("tba", None, None) == FAR_FUTURE
    assert sort_date("quarter", date(2026, 8, 1), None) == date(2026, 9, 30)
    assert is_released("quarter", date(2026, 8, 1), None, date(2026, 9, 30))
    assert not is_released("quarter", date(2026, 8, 1), None, date(2026, 9, 29))
    assert not is_released("tba", None, None, date(2100, 1, 1))


def test_release_normalizes_on_save(make_release: Callable[..., Release], switch: Platform) -> None:
    release = make_release("Future Game", switch)
    release.release_precision = "quarter"
    release.release_date = date(2099, 8, 15)
    release.release_date_end = date(2099, 1, 1)
    release.save(update_fields=["release_precision"])
    release = Release.objects.get(pk=release.pk)
    assert release.release_date == date(2099, 7, 1)
    assert release.release_date_end is None
    assert release.sort_date == date(2099, 9, 30)
    assert release.is_released is False
    release.release_precision = "tba"
    release.save()
    assert release.year is None
