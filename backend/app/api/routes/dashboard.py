from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from zoneinfo import ZoneInfo

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

router = APIRouter()
JAKARTA_TZ = ZoneInfo("Asia/Jakarta")


def current_month() -> str:
    return datetime.now(JAKARTA_TZ).strftime("%Y-%m")


def parse_month_param(month: str | None) -> date:
    value = month or current_month()
    try:
        year_text, month_text = value.split("-", maxsplit=1)
        return date(int(year_text), int(month_text), 1)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Format bulan harus YYYY-MM.",
        ) from exc


def next_month_start(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)


def add_months(month_start: date, delta: int) -> date:
    month_index = month_start.year * 12 + (month_start.month - 1) + delta
    return date(month_index // 12, (month_index % 12) + 1, 1)


def month_key(month_start: date) -> str:
    return month_start.strftime("%Y-%m")


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


def savings_rate(income_total: Decimal, net_cashflow: Decimal) -> float:
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
    month_start = parse_month_param(month)
    rows = list_all_transactions(
        transactions_repository,
        current_user["id"],
        month_start=month_start,
        next_month_start=next_month_start(month_start),
    )
    income_total, expense_total = totals(rows)
    net_cashflow = income_total - expense_total
    return DashboardSummary(
        month=month_key(month_start),
        income_total=float(income_total),
        expense_total=float(expense_total),
        net_cashflow=float(net_cashflow),
        savings_rate_percent=savings_rate(income_total, net_cashflow),
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
    month_start = parse_month_param(month)
    rows = list_all_transactions(
        transactions_repository,
        current_user["id"],
        month_start=month_start,
        next_month_start=next_month_start(month_start),
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
    end_month = parse_month_param(None)
    start_month = add_months(end_month, -(months - 1))
    rows = list_all_transactions(
        transactions_repository,
        current_user["id"],
        month_start=start_month,
        next_month_start=next_month_start(end_month),
    )
    grouped: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        transaction_date = date.fromisoformat(str(row["transaction_date"]))
        grouped[transaction_date.strftime("%Y-%m")].append(row)

    items: list[TrendItem] = []
    for index in range(months):
        current = add_months(start_month, index)
        key = month_key(current)
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
