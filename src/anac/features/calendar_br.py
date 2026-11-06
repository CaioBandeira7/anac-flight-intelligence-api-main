"""Brazilian calendar facts known long in advance. Dates are computed, never read from flights."""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl

SCHOOL_VACATION_MONTHS = frozenset({1, 7, 12})


def easter(year: int) -> date:
    """Anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month, day = divmod(h + m - 7 * n + 114, 31)
    return date(year, month, day + 1)


def carnival_days(year: int) -> tuple[date, date]:
    """Monday and Tuesday of Carnival."""
    tuesday = easter(year) - timedelta(days=47)
    return tuesday - timedelta(days=1), tuesday


def national_holidays(year: int) -> set[date]:
    """National holidays. Black Awareness Day became national in 2024 (Law 14.759/2023)."""
    fixed = {(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (12, 25)}
    days = {date(year, month, day) for month, day in fixed}
    days.add(easter(year) - timedelta(days=2))  # Good Friday
    if year >= 2024:
        days.add(date(year, 11, 20))
    return days


def daily_calendar(first: date, last: date) -> pl.DataFrame:
    """One row per date, including days around holidays and Carnival."""
    days = [first + timedelta(days=offset) for offset in range((last - first).days + 1)]
    holidays: set[date] = set()
    carnival: set[date] = set()
    for year in range(first.year - 1, last.year + 2):
        holidays |= national_holidays(year)
        carnival |= set(carnival_days(year))
    all_special = holidays | carnival
    return pl.DataFrame(
        {
            "target_date": days,
            "cal_day_of_week": [day.weekday() for day in days],
            "cal_day_of_month": [day.day for day in days],
            "cal_month": [day.month for day in days],
            "cal_week_of_year": [day.isocalendar()[1] for day in days],
            "cal_is_weekend": [day.weekday() >= 5 for day in days],
            "cal_is_holiday": [day in holidays for day in days],
            "cal_is_carnival": [day in carnival for day in days],
            "cal_is_day_before_special": [day + timedelta(days=1) in all_special for day in days],
            "cal_is_day_after_special": [day - timedelta(days=1) in all_special for day in days],
            "cal_is_school_vacation": [day.month in SCHOOL_VACATION_MONTHS for day in days],
        },
        schema_overrides={
            "target_date": pl.Date,
            "cal_day_of_week": pl.Int8,
            "cal_day_of_month": pl.Int8,
            "cal_month": pl.Int8,
            "cal_week_of_year": pl.Int8,
        },
    )


def monthly_calendar(months: list[int]) -> pl.DataFrame:
    """One row per month index with counts of the days that matter for demand."""
    rows = []
    for index in months:
        year, zero_month = divmod(index, 12)
        first = date(year, zero_month + 1, 1)
        following = date(year + (zero_month == 11), (zero_month + 1) % 12 + 1, 1)
        days = [first + timedelta(days=offset) for offset in range((following - first).days)]
        holidays = national_holidays(year)
        carnival = set(carnival_days(year))
        rows.append(
            {
                "target_month": index,
                "cal_month": zero_month + 1,
                "cal_days_in_month": len(days),
                "cal_weekend_days": sum(day.weekday() >= 5 for day in days),
                "cal_holidays": sum(day in holidays for day in days),
                "cal_has_carnival": any(day in carnival for day in days),
                "cal_is_school_vacation": zero_month + 1 in SCHOOL_VACATION_MONTHS,
            }
        )
    return pl.DataFrame(
        rows,
        schema={
            "target_month": pl.Int32,
            "cal_month": pl.Int8,
            "cal_days_in_month": pl.Int8,
            "cal_weekend_days": pl.Int8,
            "cal_holidays": pl.Int8,
            "cal_has_carnival": pl.Boolean,
            "cal_is_school_vacation": pl.Boolean,
        },
    )
