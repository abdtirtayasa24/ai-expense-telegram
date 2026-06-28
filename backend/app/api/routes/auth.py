from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user, get_settings, get_users_repository
from app.core.telegram_auth import TelegramInitDataError, validate_telegram_init_data
from app.repositories.base import Row
from app.repositories.users_repository import UsersRepository
from app.schemas.auth import (
    AuthenticatedUser,
    TelegramMiniAppAuthRequest,
    TelegramMiniAppAuthResponse,
)
from app.services.jwt_service import create_access_token

router = APIRouter()


def user_profile(user: Row) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=user["id"],
        telegram_user_id=user["telegram_user_id"],
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        role=user.get("role", "user"),
        status=user.get("status", "active"),
        currency=user.get("currency", "IDR"),
        timezone=user.get("timezone", "Asia/Jakarta"),
        cashflow_period_start_day=user.get("cashflow_period_start_day", 1),
    )


@router.post("/telegram-mini-app", response_model=TelegramMiniAppAuthResponse)
async def login_with_telegram_mini_app(
    payload: TelegramMiniAppAuthRequest,
    settings: Annotated[Any, Depends(get_settings)],
    users_repository: Annotated[UsersRepository, Depends(get_users_repository)],
) -> TelegramMiniAppAuthResponse:
    try:
        init_data = validate_telegram_init_data(
            payload.init_data,
            bot_token=settings.telegram_bot_token,
            max_age_seconds=settings.telegram_init_data_max_age_seconds,
        )
    except TelegramInitDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Data Telegram tidak valid.",
        ) from exc

    user = users_repository.get_by_telegram_user_id(init_data.user.id)
    if user is None or user.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun kamu belum terdaftar atau sudah dinonaktifkan.",
        )
    if user.get("onboarding_status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Selesaikan onboarding lewat bot terlebih dahulu.",
        )

    return TelegramMiniAppAuthResponse(
        access_token=create_access_token(user, settings),
        user=user_profile(user),
    )


@router.get("/me", response_model=AuthenticatedUser)
async def read_current_user(
    current_user: Annotated[Row, Depends(get_current_user)],
) -> AuthenticatedUser:
    return user_profile(current_user)
