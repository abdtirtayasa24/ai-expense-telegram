from __future__ import annotations

from datetime import date

from app.services.cashflow_period import period_for_reference_date


def test_period_for_reference_date_uses_payday_cycle() -> None:
    period_start, period_end = period_for_reference_date(date(2026, 7, 3), 29)

    assert period_start == date(2026, 6, 29)
    assert period_end == date(2026, 7, 29)


def test_period_for_reference_date_clamps_day_for_short_months() -> None:
    period_start, period_end = period_for_reference_date(date(2026, 2, 28), 31)

    assert period_start == date(2026, 2, 28)
    assert period_end == date(2026, 3, 31)

    previous_start, previous_end = period_for_reference_date(date(2026, 2, 27), 31)
    assert previous_start == date(2026, 1, 31)
    assert previous_end == date(2026, 2, 28)
