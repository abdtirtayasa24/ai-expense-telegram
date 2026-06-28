from calendar import monthrange
from datetime import date, datetime
from zoneinfo import ZoneInfo

JAKARTA_TZ = ZoneInfo("Asia/Jakarta")


def today_jakarta() -> date:
    return datetime.now(JAKARTA_TZ).date()


def clamp_day(year: int, month: int, day: int) -> int:
    return min(day, monthrange(year, month)[1])


def add_months(value: date, delta: int) -> date:
    month_index = value.year * 12 + (value.month - 1) + delta
    return date(month_index // 12, (month_index % 12) + 1, 1)


def period_start_for_month(month_start: date, start_day: int) -> date:
    return date(
        month_start.year,
        month_start.month,
        clamp_day(month_start.year, month_start.month, start_day),
    )


def period_for_reference_date(
    reference_date: date,
    start_day: int,
) -> tuple[date, date]:
    current_month_start = date(reference_date.year, reference_date.month, 1)
    current_start = period_start_for_month(current_month_start, start_day)
    if reference_date < current_start:
        start_month = add_months(current_month_start, -1)
        period_start = period_start_for_month(start_month, start_day)
        period_end = current_start
        return period_start, period_end

    next_month_start = add_months(current_month_start, 1)
    period_end = period_start_for_month(next_month_start, start_day)
    return current_start, period_end


def current_cashflow_period(start_day: int) -> tuple[date, date]:
    return period_for_reference_date(today_jakarta(), start_day)


def cashflow_period_key(period_start: date) -> str:
    return period_start.strftime("%Y-%m-%d")


def user_cashflow_start_day(user: dict) -> int:
    value = user.get("cashflow_period_start_day", 1)
    if isinstance(value, int) and 1 <= value <= 31:
        return value
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 1
    if 1 <= parsed <= 31:
        return parsed
    return 1
