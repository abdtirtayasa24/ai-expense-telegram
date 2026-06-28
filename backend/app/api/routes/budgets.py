from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import (
    get_budgets_repository,
    get_current_user,
    get_transactions_repository,
)
from app.repositories.base import Row
from app.repositories.budgets_repository import BudgetsRepository
from app.repositories.transactions_repository import TransactionsRepository
from app.schemas.budget import (
    BudgetCreate,
    BudgetDeleteResponse,
    BudgetListResponse,
    BudgetOut,
    BudgetUpdate,
)
from app.services.cashflow_period import (
    add_months,
    current_cashflow_period,
    period_for_reference_date,
    period_start_for_month,
    user_cashflow_start_day,
)

router = APIRouter()


def budget_out(
    row: Row,
    actual: Decimal,
) -> BudgetOut:
    monthly_limit = Decimal(str(row["monthly_limit"]))
    remaining = monthly_limit - actual
    percent_used = float(
        (actual / monthly_limit * Decimal("100")).quantize(Decimal("0.01"))
    ) if monthly_limit > 0 else 0.0
    return BudgetOut(
        id=row["id"],
        category=row["category"],
        monthly_limit=float(monthly_limit),
        month=date.fromisoformat(str(row["month"])),
        actual=float(actual),
        remaining=float(remaining),
        percent_used=min(percent_used, 999.99),
    )


def category_actuals(
    transactions_repository: TransactionsRepository,
    user_id: str,
    month_start: date,
    next_month_start: date,
) -> dict[str, Decimal]:
    """Return category→actual expense totals for the current user period."""
    from app.api.routes.dashboard import list_all_transactions

    rows = list_all_transactions(
        transactions_repository,
        user_id,
        month_start=month_start,
        next_month_start=next_month_start,
        transaction_type="expense",
    )
    totals: dict[str, Decimal] = {}
    for row in rows:
        category = str(row["category"])
        amount = Decimal(str(row["amount"]))
        totals[category] = totals.get(category, Decimal("0")) + amount
    return totals


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
    month_start = parse_month_param(month)
    period_start = period_start_for_month(month_start, start_day)
    next_start = period_start_for_month(add_months(month_start, 1), start_day)
    return period_start, next_start


@router.get("", response_model=BudgetListResponse)
async def list_budgets(
    current_user: Annotated[Row, Depends(get_current_user)],
    budgets_repository: Annotated[BudgetsRepository, Depends(get_budgets_repository)],
    transactions_repository: Annotated[
        TransactionsRepository,
        Depends(get_transactions_repository),
    ],
    month: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$")] = None,
) -> BudgetListResponse:
    start_day = user_cashflow_start_day(current_user)
    month_start, next_start = period_bounds(month, start_day)
    actuals = category_actuals(
        transactions_repository,
        current_user["id"],
        month_start,
        next_start,
    )
    rows = budgets_repository.list_for_user_month(
        current_user["id"],
        month_start,
    )
    items = [
        budget_out(row, actuals.get(str(row["category"]), Decimal("0")))
        for row in rows
    ]
    return BudgetListResponse(items=items)


@router.post("", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
async def create_budget(
    payload: BudgetCreate,
    current_user: Annotated[Row, Depends(get_current_user)],
    budgets_repository: Annotated[BudgetsRepository, Depends(get_budgets_repository)],
    transactions_repository: Annotated[
        TransactionsRepository,
        Depends(get_transactions_repository),
    ],
) -> BudgetOut:
    start_day = user_cashflow_start_day(current_user)
    month_start, next_start = (
        period_for_reference_date(payload.month, start_day)
        if payload.month is not None
        else current_cashflow_period(start_day)
    )

    # Check for duplicate before creating
    existing = budgets_repository.list_for_user_month(
        current_user["id"],
        month_start,
    )
    if any(
        str(row["category"]) == payload.category
        for row in existing
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Budget untuk kategori dan bulan ini sudah ada.",
        )

    row = budgets_repository.create(
        user_id=current_user["id"],
        category=payload.category,
        monthly_limit=payload.monthly_limit,
        month=month_start,
    )

    actual = category_actuals(
        transactions_repository,
        current_user["id"],
        month_start,
        next_start,
    ).get(payload.category, Decimal("0"))
    return budget_out(row, actual)


@router.patch("/{budget_id}", response_model=BudgetOut)
async def update_budget(
    budget_id: str,
    payload: BudgetUpdate,
    current_user: Annotated[Row, Depends(get_current_user)],
    budgets_repository: Annotated[BudgetsRepository, Depends(get_budgets_repository)],
    transactions_repository: Annotated[
        TransactionsRepository,
        Depends(get_transactions_repository),
    ],
) -> BudgetOut:
    row = budgets_repository.update_for_user(
        budget_id,
        current_user["id"],
        payload.model_dump(exclude_unset=True),
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget tidak ditemukan.",
        )

    start_day = user_cashflow_start_day(current_user)
    month_start = date.fromisoformat(str(row["month"]))
    next_start = period_start_for_month(
        add_months(date(month_start.year, month_start.month, 1), 1),
        start_day,
    )
    actual = category_actuals(
        transactions_repository,
        current_user["id"],
        month_start,
        next_start,
    ).get(str(row["category"]), Decimal("0"))
    return budget_out(row, actual)


@router.delete("/{budget_id}", response_model=BudgetDeleteResponse)
async def delete_budget(
    budget_id: str,
    current_user: Annotated[Row, Depends(get_current_user)],
    budgets_repository: Annotated[BudgetsRepository, Depends(get_budgets_repository)],
) -> BudgetDeleteResponse:
    deleted = budgets_repository.delete_for_user(budget_id, current_user["id"])
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget tidak ditemukan.",
        )
    return BudgetDeleteResponse(deleted=True)
