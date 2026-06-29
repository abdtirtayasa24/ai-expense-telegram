from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user, get_transactions_repository
from app.api.routes.transactions import transaction_out
from app.repositories.base import Row
from app.repositories.transactions_repository import TransactionsRepository
from app.schemas.dashboard import (
    CategoryBreakdownItem,
    CategoryBreakdownResponse,
    DashboardSummary,
    RecentTransactionsResponse,
    TrendItem,
    TrendResponse,
)
from app.services.cashflow_period import (
    add_months,
    current_cashflow_period,
    period_start_for_month,
    user_cashflow_start_day,
)

router = APIRouter()


def parse_month_param(month: str) -> date:
    try:
        year_text, month_text = month.split("-", maxsplit=1)
        return date(int(year_text), int(month_text), 1)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Format bulan harus YYYY-MM.",
        ) from exc


def period_bounds(month: str | None, start_day: int) -> tuple[date, date]:
    if month is None:
        return current_cashflow_period(start_day)
    period_start = period_start_for_month(parse_month_param(month), start_day)
    next_period_start = period_start_for_month(
        add_months(date(period_start.year, period_start.month, 1), 1),
        start_day,
    )
    return period_start, next_period_start


def period_key(period_start: date, start_day: int) -> str:
    if start_day == 1:
        return period_start.strftime("%Y-%m")
    return period_start.isoformat()


def row_amount(row: Row) -> Decimal:
    return Decimal(str(row["amount"]))


def totals(rows: list[Row]) -> tuple[Decimal, Decimal]:
    income = Decimal("0")
    expense = Decimal("0")
    for row in rows:
        if row.get("type") == "income":
            income += row_amount(row)
        elif row.get("type") == "expense":
            expense += row_amount(row)
    return income, expense


def list_all_transactions(
    transactions_repository: TransactionsRepository,
    user_id: str,
    month_start: date | None = None,
    next_month_start: date | None = None,
    transaction_type: str | None = None,
    page_size: int = 1000,
) -> list[Row]:
    rows: list[Row] = []
    offset = 0
    while True:
        page = transactions_repository.list_for_user(
            user_id,
            month_start=month_start,
            next_month_start=next_month_start,
            transaction_type=transaction_type,  # type: ignore[arg-type]
            limit=page_size,
            offset=offset,
        )
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += page_size


def surplus_rate(income_total: Decimal, net_cashflow: Decimal) -> float:
    if income_total <= 0:
        return 0.0
    rate = net_cashflow / income_total * Decimal("100")
    return float(rate.quantize(Decimal("0.01")))


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    current_user: Annotated[Row, Depends(get_current_user)],
    transactions_repository: Annotated[
        TransactionsRepository,
        Depends(get_transactions_repository),
    ],
    month: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$")] = None,
) -> DashboardSummary:
    start_day = user_cashflow_start_day(current_user)
    month_start, next_start = period_bounds(month, start_day)
    rows = list_all_transactions(
        transactions_repository,
        current_user["id"],
        month_start=month_start,
        next_month_start=next_start,
    )
    income_total, expense_total = totals(rows)
    net_cashflow = income_total - expense_total
    return DashboardSummary(
        month=period_key(month_start, start_day),
        income_total=float(income_total),
        expense_total=float(expense_total),
        net_cashflow=float(net_cashflow),
        surplus_rate_percent=surplus_rate(income_total, net_cashflow),
    )


@router.get("/categories", response_model=CategoryBreakdownResponse)
async def dashboard_categories(
    current_user: Annotated[Row, Depends(get_current_user)],
    transactions_repository: Annotated[
        TransactionsRepository,
        Depends(get_transactions_repository),
    ],
    month: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$")] = None,
) -> CategoryBreakdownResponse:
    start_day = user_cashflow_start_day(current_user)
    month_start, next_start = period_bounds(month, start_day)
    rows = list_all_transactions(
        transactions_repository,
        current_user["id"],
        month_start=month_start,
        next_month_start=next_start,
        transaction_type="expense",
    )
    amounts: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in rows:
        amounts[str(row["category"])] += row_amount(row)
    total_expense = sum(amounts.values(), Decimal("0"))
    if total_expense <= 0:
        return CategoryBreakdownResponse(items=[])
    sorted_amounts = sorted(
        amounts.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    items = [
        CategoryBreakdownItem(
            category=category,
            amount=float(amount),
            percent=float(
                (amount / total_expense * Decimal("100")).quantize(
                    Decimal("0.01"),
                ),
            ),
        )
        for category, amount in sorted_amounts
    ]
    return CategoryBreakdownResponse(items=items)


@router.get("/trend", response_model=TrendResponse)
async def dashboard_trend(
    current_user: Annotated[Row, Depends(get_current_user)],
    transactions_repository: Annotated[
        TransactionsRepository,
        Depends(get_transactions_repository),
    ],
    months: Annotated[int, Query(ge=1, le=24)] = 6,
) -> TrendResponse:
    start_day = user_cashflow_start_day(current_user)
    end_month, end_next = current_cashflow_period(start_day)
    start_month = period_start_for_month(
        add_months(date(end_month.year, end_month.month, 1), -(months - 1)),
        start_day,
    )
    rows = list_all_transactions(
        transactions_repository,
        current_user["id"],
        month_start=start_month,
        next_month_start=end_next,
    )
    grouped: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        transaction_date = date.fromisoformat(str(row["transaction_date"]))
        period_start, _ = period_bounds(transaction_date.strftime("%Y-%m"), start_day)
        if transaction_date < period_start:
            period_start = period_start_for_month(
                add_months(date(period_start.year, period_start.month, 1), -1),
                start_day,
            )
        grouped[period_key(period_start, start_day)].append(row)

    items: list[TrendItem] = []
    for index in range(months):
        current = period_start_for_month(
            add_months(date(start_month.year, start_month.month, 1), index),
            start_day,
        )
        key = period_key(current, start_day)
        income_total, expense_total = totals(grouped[key])
        items.append(
            TrendItem(
                month=key,
                income_total=float(income_total),
                expense_total=float(expense_total),
                net_cashflow=float(income_total - expense_total),
            )
        )
    return TrendResponse(items=items)


@router.get("/recent-transactions", response_model=RecentTransactionsResponse)
async def dashboard_recent_transactions(
    current_user: Annotated[Row, Depends(get_current_user)],
    transactions_repository: Annotated[
        TransactionsRepository,
        Depends(get_transactions_repository),
    ],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> RecentTransactionsResponse:
    rows = transactions_repository.list_for_user(current_user["id"], limit=limit)
    return RecentTransactionsResponse(items=[transaction_out(row) for row in rows])
