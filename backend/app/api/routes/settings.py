from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user, get_users_repository
from app.repositories.base import Row
from app.repositories.users_repository import UsersRepository
from app.schemas.settings import CashflowPeriodUpdate, UserSettingsOut
from app.services.cashflow_period import user_cashflow_start_day

router = APIRouter()


def settings_out(user: Row) -> UserSettingsOut:
    return UserSettingsOut(
        cashflow_period_start_day=user_cashflow_start_day(user),
    )


@router.get("", response_model=UserSettingsOut)
async def read_settings(
    current_user: Annotated[Row, Depends(get_current_user)],
) -> UserSettingsOut:
    return settings_out(current_user)


@router.patch("/cashflow-period", response_model=UserSettingsOut)
async def update_cashflow_period(
    payload: CashflowPeriodUpdate,
    current_user: Annotated[Row, Depends(get_current_user)],
    users_repository: Annotated[UsersRepository, Depends(get_users_repository)],
) -> UserSettingsOut:
    updated = users_repository.update_cashflow_period_start_day(
        current_user["id"],
        payload.cashflow_period_start_day,
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pengaturan tidak ditemukan.",
        )
    return settings_out(updated)
