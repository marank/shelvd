"""Release date periods: precision + first day → (start, end, sort date)."""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from .choices import DatePrecision

# Unknown dates sort after everything else.
FAR_FUTURE = date(2999, 12, 31)


def period(
    precision: str, start: date | None, end: date | None = None
) -> tuple[date | None, date | None]:
    """Normalize the start to the period's first day and compute its last day."""
    if precision == DatePrecision.TBA or start is None:
        return None, None
    if precision == DatePrecision.DAY:
        return start, start
    if precision == DatePrecision.WEEK:
        monday = start - timedelta(days=start.weekday())
        return monday, monday + timedelta(days=6)
    if precision == DatePrecision.MONTH:
        last = calendar.monthrange(start.year, start.month)[1]
        return start.replace(day=1), start.replace(day=last)
    if precision == DatePrecision.QUARTER:
        first_month = (start.month - 1) // 3 * 3 + 1
        last_month = first_month + 2
        last = calendar.monthrange(start.year, last_month)[1]
        return date(start.year, first_month, 1), date(start.year, last_month, last)
    if precision == DatePrecision.HALF:
        if start.month <= 6:
            return date(start.year, 1, 1), date(start.year, 6, 30)
        return date(start.year, 7, 1), date(start.year, 12, 31)
    if precision == DatePrecision.YEAR:
        return date(start.year, 1, 1), date(start.year, 12, 31)
    # WINDOW
    return start, max(end or start, start)


def sort_date(precision: str, start: date | None, end: date | None) -> date:
    """The day a release is surely out: the end of its period (unknown: far future)."""
    _, last = period(precision, start, end)
    return last or FAR_FUTURE


def is_released(precision: str, start: date | None, end: date | None, today: date) -> bool:
    _, last = period(precision, start, end)
    return last is not None and last <= today
