from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError

from app.repositories.base import Row
from app.repositories.budgets_repository import BudgetsRepository
from app.repositories.transactions_repository import TransactionsRepository
from app.repositories.users_repository import UsersRepository
from app.services.jwt_service import decode_access_token


def get_settings() -> Any:
    from app.core.config import settings

    return settings


def get_users_repository() -> UsersRepository:
    return UsersRepository()


def get_transactions_repository() -> TransactionsRepository:
    return TransactionsRepository()


def get_budgets_repository() -> BudgetsRepository:
    return BudgetsRepository()


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    settings: Annotated[Any, Depends(get_settings)] = None,
    users_repository: Annotated[UsersRepository, Depends(get_users_repository)] = None,
) -> Row:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid.",
        )

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token, settings)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid.",
        ) from exc

    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid.",
        )

    user = users_repository.get_by_id(user_id)
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
    return user
