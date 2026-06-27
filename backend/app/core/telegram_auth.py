import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl

from pydantic import BaseModel, ValidationError


class TelegramInitDataUser(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None


class TelegramInitData(BaseModel):
    user: TelegramInitDataUser
    auth_date: int


class TelegramInitDataError(ValueError):
    pass


def validate_telegram_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int,
) -> TelegramInitData:
    try:
        params = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    except ValueError as exc:
        raise TelegramInitDataError("Malformed initData.") from exc

    received_hash = params.pop("hash", None)
    if not received_hash:
        raise TelegramInitDataError("Missing hash.")

    auth_date = params.get("auth_date")
    user_json = params.get("user")
    if not auth_date or not user_json:
        raise TelegramInitDataError("Missing required fields.")

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(params.items())
    )
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode(),
        hashlib.sha256,
    ).digest()
    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise TelegramInitDataError("Invalid hash.")

    try:
        auth_timestamp = int(auth_date)
    except ValueError as exc:
        raise TelegramInitDataError("Invalid auth_date.") from exc

    age_seconds = datetime.now(UTC).timestamp() - auth_timestamp
    if age_seconds < 0 or age_seconds > max_age_seconds:
        raise TelegramInitDataError("Stale auth_date.")

    try:
        user_data: Any = json.loads(user_json)
        user = TelegramInitDataUser.model_validate(user_data)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise TelegramInitDataError("Invalid user.") from exc

    return TelegramInitData(user=user, auth_date=auth_timestamp)
