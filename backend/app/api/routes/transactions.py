from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user, get_transactions_repository
from app.repositories.base import Row
from app.repositories.transactions_repository import TransactionsRepository
from app.schemas.parser import TransactionCategory
from app.schemas.transaction import (
    TransactionCreate,
    TransactionDeleteResponse,
    TransactionListResponse,
    TransactionOut,
    TransactionType,
    TransactionUpdate,
)

router = APIRouter()


def transaction_out(row: Row) -> TransactionOut:
    return TransactionOut(
        id=row["id"],
        type=row["type"],
        name=row["name"],
        category=row["category"],
        amount=float(Decimal(str(row["amount"]))),
        transaction_date=date.fromisoformat(str(row["transaction_date"])),
        note=row.get("note"),
        source=row.get("source", "manual"),
        parser=row.get("parser", "manual"),
        confidence_score=(
            float(row["confidence_score"])
            if row.get("confidence_score") is not None
            else None
        ),
    )


def parse_month(month: str | None) -> tuple[date | None, date | None]:
    if month is None:
        return None, None
    try:
        year_text, month_text = month.split("-", maxsplit=1)
        year = int(year_text)
        month_number = int(month_text)
        month_start = date(year, month_number, 1)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Format bulan harus YYYY-MM.",
        ) from exc
    _, days_in_month = monthrange(month_start.year, month_start.month)
    if month_start.month == 12:
        next_month_start = date(month_start.year + 1, 1, 1)
    else:
        next_month_start = date(month_start.year, month_start.month + 1, 1)
    # monthrange validates date; keep days_in_month read to document range validation.
    _ = days_in_month
    return month_start, next_month_start


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    current_user: Annotated[Row, Depends(get_current_user)],
    transactions_repository: Annotated[
        TransactionsRepository,
        Depends(get_transactions_repository),
    ],
    month: Annotated[
        str | None,
        Query(pattern=r"^\d{4}-\d{2}$"),
    ] = None,
    type: TransactionType | None = None,
    category: TransactionCategory | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TransactionListResponse:
    month_start, next_month_start = parse_month(month)
    rows = transactions_repository.list_for_user(
        current_user["id"],
        month_start=month_start,
        next_month_start=next_month_start,
        transaction_type=type,
        category=category,
        limit=limit,
        offset=offset,
    )
    return TransactionListResponse(
        items=[transaction_out(row) for row in rows],
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionCreate,
    current_user: Annotated[Row, Depends(get_current_user)],
    transactions_repository: Annotated[
        TransactionsRepository,
        Depends(get_transactions_repository),
    ],
) -> TransactionOut:
    row = transactions_repository.create(
        user_id=current_user["id"],
        transaction_type=payload.type,
        name=payload.name,
        category=payload.category,
        amount=payload.amount,
        transaction_date=payload.transaction_date,
        note=payload.note,
        source="manual",
        parser="manual",
    )
    return transaction_out(row)


@router.patch("/{transaction_id}", response_model=TransactionOut)
async def update_transaction(
    transaction_id: str,
    payload: TransactionUpdate,
    current_user: Annotated[Row, Depends(get_current_user)],
    transactions_repository: Annotated[
        TransactionsRepository,
        Depends(get_transactions_repository),
    ],
) -> TransactionOut:
    row = transactions_repository.update_for_user(
        transaction_id,
        current_user["id"],
        payload.model_dump(exclude_unset=True),
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaksi tidak ditemukan.",
        )
    return transaction_out(row)


@router.delete("/{transaction_id}", response_model=TransactionDeleteResponse)
async def delete_transaction(
    transaction_id: str,
    current_user: Annotated[Row, Depends(get_current_user)],
    transactions_repository: Annotated[
        TransactionsRepository,
        Depends(get_transactions_repository),
    ],
) -> TransactionDeleteResponse:
    deleted = transactions_repository.delete_for_user(
        transaction_id,
        current_user["id"],
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaksi tidak ditemukan.",
        )
    return TransactionDeleteResponse(deleted=True)
