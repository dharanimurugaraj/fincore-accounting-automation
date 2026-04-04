"""
Date range, period parsing, weekday checks.
"""

import calendar
from datetime import date, timedelta
from typing import List, Tuple


def parse_statement_month(month_str: str) -> Tuple[int, int]:
    """Parse '2026-02' into (2026, 2)."""
    parts = month_str.split("-")
    return int(parts[0]), int(parts[1])


def get_month_date_range(year: int, month: int) -> Tuple[date, date]:
    """Return (first_day, last_day) for a given month."""
    first = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    last = date(year, month, last_day)
    return first, last


def get_all_dates_in_month(year: int, month: int) -> List[date]:
    """Return all dates in the given month."""
    last_day = calendar.monthrange(year, month)[1]
    return [date(year, month, d) for d in range(1, last_day + 1)]


def is_business_day(dt: date) -> bool:
    """Check if a date is a weekday (Mon-Fri)."""
    return dt.weekday() < 5


def days_between(start: date, end: date) -> int:
    """Return number of days between two dates."""
    return (end - start).days
