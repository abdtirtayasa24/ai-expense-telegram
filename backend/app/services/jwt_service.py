from datetime import UTC, datetime, timedelta
from typing import Any

from jose import jwt

from app.repositories.base import Row


def create_access_token(user: Row, settings: Any) -> str:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.jwt_expires_minutes)
    payload = {
        "sub": user["id"],
        "telegram_user_id": user["telegram_user_id"],
        "role": user.get("role", "user"),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str, settings: Any) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
