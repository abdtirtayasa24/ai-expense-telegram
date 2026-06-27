from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

from fastapi.testclient import TestClient

from app.api.dependencies import get_settings, get_users_repository
from app.main import app


@dataclass
class FakeSettings:
    telegram_bot_token: str = "test-token"
    jwt_secret_key: str = "test-secret"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60
    telegram_init_data_max_age_seconds: int = 86400


class FakeUsersRepository:
    def __init__(self) -> None:
        self.users: dict[int, dict[str, Any]] = {}

    def add_user(
        self,
        telegram_user_id: int,
        status: str = "active",
        onboarding_status: str = "completed",
    ) -> dict[str, Any]:
        row = {
            "id": f"user-{telegram_user_id}",
            "telegram_user_id": telegram_user_id,
            "first_name": "Budi",
            "last_name": "Santoso",
            "role": "user",
            "status": status,
            "onboarding_status": onboarding_status,
            "currency": "IDR",
            "timezone": "Asia/Jakarta",
        }
        self.users[telegram_user_id] = row
        return row

    def get_by_telegram_user_id(self, telegram_user_id: int) -> dict[str, Any] | None:
        return self.users.get(telegram_user_id)

    def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        return next(
            (row for row in self.users.values() if row["id"] == user_id),
            None,
        )


def make_init_data(
    bot_token: str,
    telegram_user_id: int = 111,
    auth_date: int | None = None,
    first_name: str = "Budi",
) -> str:
    auth_timestamp = auth_date or int(datetime.now(UTC).timestamp())
    params = {
        "auth_date": str(auth_timestamp),
        "query_id": "test-query",
        "user": json.dumps(
            {"id": telegram_user_id, "first_name": first_name},
            separators=(",", ":"),
        ),
    }
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(params.items())
    )
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode(),
        hashlib.sha256,
    ).digest()
    signature = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    encoded_params = [f"{key}={quote(value)}" for key, value in params.items()]
    encoded_params.append(f"hash={signature}")
    return "&".join(encoded_params)


def auth_client(repository: FakeUsersRepository) -> TestClient:
    app.dependency_overrides[get_settings] = lambda: FakeSettings()
    app.dependency_overrides[get_users_repository] = lambda: repository
    return TestClient(app)


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_mini_app_login_success_returns_jwt_and_profile() -> None:
    repository = FakeUsersRepository()
    repository.add_user(111)
    client = auth_client(repository)

    try:
        response = client.post(
            "/auth/telegram-mini-app",
            json={"init_data": make_init_data("test-token", 111)},
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"] == {
        "id": "user-111",
        "telegram_user_id": 111,
        "first_name": "Budi",
        "last_name": "Santoso",
        "role": "user",
        "status": "active",
        "currency": "IDR",
        "timezone": "Asia/Jakarta",
    }


def test_mini_app_login_rejects_invalid_hash() -> None:
    repository = FakeUsersRepository()
    repository.add_user(111)
    client = auth_client(repository)
    init_data = make_init_data("test-token", 111).replace("hash=", "hash=bad")

    try:
        response = client.post("/auth/telegram-mini-app", json={"init_data": init_data})
    finally:
        clear_overrides()

    assert response.status_code == 401
    assert response.json() == {"detail": "Data Telegram tidak valid."}


def test_mini_app_login_rejects_stale_init_data() -> None:
    repository = FakeUsersRepository()
    repository.add_user(111)
    client = auth_client(repository)
    old_auth_date = int((datetime.now(UTC) - timedelta(days=2)).timestamp())

    try:
        response = client.post(
            "/auth/telegram-mini-app",
            json={"init_data": make_init_data("test-token", 111, old_auth_date)},
        )
    finally:
        clear_overrides()

    assert response.status_code == 401
    assert response.json() == {"detail": "Data Telegram tidak valid."}


def test_mini_app_login_rejects_malformed_data() -> None:
    repository = FakeUsersRepository()
    client = auth_client(repository)

    try:
        response = client.post(
            "/auth/telegram-mini-app",
            json={"init_data": "auth_date=not-a-date&user=not-json"},
        )
    finally:
        clear_overrides()

    assert response.status_code == 401
    assert response.json() == {"detail": "Data Telegram tidak valid."}


def test_mini_app_login_rejects_missing_inactive_and_pending_users() -> None:
    repository = FakeUsersRepository()
    repository.add_user(222, status="inactive")
    repository.add_user(333, onboarding_status="pending")
    client = auth_client(repository)

    try:
        missing = client.post(
            "/auth/telegram-mini-app",
            json={"init_data": make_init_data("test-token", 111)},
        )
        inactive = client.post(
            "/auth/telegram-mini-app",
            json={"init_data": make_init_data("test-token", 222)},
        )
        pending = client.post(
            "/auth/telegram-mini-app",
            json={"init_data": make_init_data("test-token", 333)},
        )
    finally:
        clear_overrides()

    assert missing.status_code == 403
    assert missing.json() == {
        "detail": "Akun kamu belum terdaftar atau sudah dinonaktifkan."
    }
    assert inactive.status_code == 403
    assert inactive.json() == {
        "detail": "Akun kamu belum terdaftar atau sudah dinonaktifkan."
    }
    assert pending.status_code == 403
    assert pending.json() == {
        "detail": "Selesaikan onboarding lewat bot terlebih dahulu."
    }


def test_protected_auth_me_validates_jwt_and_current_user_state() -> None:
    repository = FakeUsersRepository()
    repository.add_user(111)
    client = auth_client(repository)

    try:
        login = client.post(
            "/auth/telegram-mini-app",
            json={"init_data": make_init_data("test-token", 111)},
        )
        token = login.json()["access_token"]
        success = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        unauthorized = client.get("/auth/me")
        repository.users[111]["status"] = "inactive"
        inactive = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    finally:
        clear_overrides()

    assert success.status_code == 200
    assert success.json()["telegram_user_id"] == 111
    assert unauthorized.status_code == 401
    assert inactive.status_code == 403
