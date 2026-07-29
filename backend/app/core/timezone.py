"""Timezone helpers. All timestamps are stored in UTC; due-date/overdue
comparisons and reminder scheduling math explicitly convert to Asia/Kolkata
at evaluation time, per design.md.
"""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")
IST = ZoneInfo("Asia/Kolkata")


def now_utc() -> datetime:
    return datetime.now(UTC)


def to_ist(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(IST)


def ist_end_of_day(d: date) -> datetime:
    """23:59:59 Asia/Kolkata on date `d`, returned as a UTC-aware datetime."""
    end_of_day_ist = datetime.combine(d, time(23, 59, 59), tzinfo=IST)
    return end_of_day_ist.astimezone(UTC)
