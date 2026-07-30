"""Recurrence engine: generate occurrence dates for a recurrence profile.

Supports: weekly, monthly_nth_day, monthly_last_day, monthly_last_bday,
quarterly, yearly. Applies business-day rules (prev/next business day) using an
optional holiday calendar (Decision #9/#13).
"""

import calendar
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.meta import CodeValue
from app.models.scheduling import HolidayCalendarDay, RecurrenceProfile

WEEKDAYS = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}


def _code(db: Session, cv_id) -> str | None:
    if cv_id is None:
        return None
    cv = db.get(CodeValue, cv_id)
    return cv.code if cv else None


def _holidays(db: Session, calendar_id) -> set[date]:
    if calendar_id is None:
        return set()
    rows = db.execute(
        select(HolidayCalendarDay.holiday_date).where(
            HolidayCalendarDay.calendar_id == calendar_id
        )
    ).scalars()
    return set(rows)


def _is_business_day(d: date, holidays: set[date]) -> bool:
    return d.weekday() < 5 and d not in holidays


def _apply_bday_rule(d: date, rule: str | None, holidays: set[date]) -> date:
    if not rule or rule == "none":
        return d
    step = 1 if rule == "next_bday" else -1
    cur = d
    guard = 0
    while not _is_business_day(cur, holidays) and guard < 31:
        cur = cur + timedelta(days=step)
        guard += 1
    return cur


def _last_day_of_month(y: int, m: int) -> date:
    return date(y, m, calendar.monthrange(y, m)[1])


def _last_business_day(y: int, m: int, holidays: set[date]) -> date:
    d = _last_day_of_month(y, m)
    while not _is_business_day(d, holidays):
        d = d - timedelta(days=1)
    return d


def _add_months(d: date, months: int) -> date:
    total = d.month - 1 + months
    y = d.year + total // 12
    m = total % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)


def occurrences(
    db: Session, profile: RecurrenceProfile, until: date, start_from: date | None = None
) -> list[date]:
    """Return occurrence dates from profile.start_date (or start_from) to `until`."""
    freq = _code(db, profile.frequency_type_cv_id) or "monthly_nth_day"
    rule = _code(db, profile.business_day_rule_cv_id)
    holidays = _holidays(db, profile.holiday_calendar_id)
    cfg = profile.config or {}

    begin = max(profile.start_date, start_from) if start_from else profile.start_date
    end = min(until, profile.end_date) if profile.end_date else until
    results: list[date] = []

    if freq == "weekly":
        weekday = WEEKDAYS.get(str(cfg.get("weekday", "MON")).upper(), 0)
        interval = int(cfg.get("interval_weeks", 1))
        d = profile.start_date
        # advance to first matching weekday
        while d.weekday() != weekday:
            d = d + timedelta(days=1)
        while d <= end:
            if d >= begin:
                results.append(_apply_bday_rule(d, rule, holidays))
            d = d + timedelta(weeks=interval)

    elif freq in ("monthly_nth_day", "monthly_last_day", "monthly_last_bday", "quarterly", "yearly"):
        step = {"monthly_nth_day": 1, "monthly_last_day": 1, "monthly_last_bday": 1,
                "quarterly": 3, "yearly": 12}[freq]
        nth = int(cfg.get("nth", profile.start_date.day))
        cursor = date(profile.start_date.year, profile.start_date.month, 1)
        while cursor <= end:
            if freq == "monthly_last_day":
                occ = _last_day_of_month(cursor.year, cursor.month)
            elif freq == "monthly_last_bday":
                occ = _last_business_day(cursor.year, cursor.month, holidays)
            else:
                last = calendar.monthrange(cursor.year, cursor.month)[1]
                occ = date(cursor.year, cursor.month, min(nth, last))
            if begin <= occ <= end:
                results.append(_apply_bday_rule(occ, rule, holidays))
            cursor = _add_months(cursor, step)

    return sorted(set(results))