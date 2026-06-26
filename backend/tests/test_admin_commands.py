from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.bot import responses
from app.bot.commands import handle_admin_command
from app.bot.webhook import (
    get_settings,
    get_telegram_client,
    get_transactions_repository,
    get_users_repository,
)
from app.main import app

pytestmark = pytest.mark.asyncio


class FakeUsersRepository:
    def __init__(self) -> None:
        self.users: dict[int, dict[str, Any]] = {}

    def get_by_telegram_user_id(self, telegram_user_id: int) -> dict[str, Any] | None:
        return self.users.get(telegram_user_id)

    def create_registered_user(
        self,
        telegram_user_id: int,
        registered_by_telegram_id: int,
        telegram_username: str | None = None,
        role: str = "user",
    ) -> dict[str, Any]:
        row = {
            "id": f"user-{telegram_user_id}",
            "telegram_user_id": telegram_user_id,
            "telegram_username": telegram_username,
            "first_name": None,
            "last_name": None,
            "role": role,
            "status": "active",
            "onboarding_status": "pending",
            "registered_by_telegram_id": registered_by_telegram_id,
            "unregistered_at": None,
            "created_at": str(telegram_user_id),
        }
        self.users[telegram_user_id] = row
        return row

    def reactivate(
        self,
        telegram_user_id: int,
        registered_by_telegram_id: int,
        reset_onboarding: bool = False,
    ) -> dict[str, Any] | None:
        row = self.users.get(telegram_user_id)
        if row is None:
            return None
        row["status"] = "active"
        row["registered_by_telegram_id"] = registered_by_telegram_id
        row["unregistered_at"] = None
        if reset_onboarding:
            row["onboarding_status"] = "pending"
        return row

    def deactivate(self, telegram_user_id: int) -> dict[str, Any] | None:
        row = self.users.get(telegram_user_id)
        if row is None:
            return None
        row["status"] = "inactive"
        row["unregistered_at"] = "now"
        return row

    def list_users(self) -> list[dict[str, Any]]:
        return list(self.users.values())


class FakeTransactionsRepository:
    def __init__(self) -> None:
        self.transactions: list[dict[str, Any]] = []


class FakeTelegramClient:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict | None = None,
    ) -> dict[str, bool]:
        self.messages.append((chat_id, text))
        return {"ok": True}


class FailingTelegramClient:
    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict | None = None,
    ) -> None:
        raise RuntimeError("Telegram API unavailable")


@dataclass
class FakeSettings:
    telegram_bot_token: str = "test-token"
    admin_telegram_id: int = 999
    parser_confidence_threshold: float = 0.75


async def run_command(
    text: str,
    sender_id: int,
    repository: FakeUsersRepository,
    telegram_client: FakeTelegramClient,
    chat_id: int = 1234,
) -> bool:
    return await handle_admin_command(
        text=text,
        sender_telegram_user_id=sender_id,
        chat_id=chat_id,
        admin_telegram_id=999,
        users_repository=repository,  # type: ignore[arg-type]
        telegram_client=telegram_client,
    )


async def test_admin_register_creates_active_pending_user() -> None:
    repository = FakeUsersRepository()
    telegram_client = FakeTelegramClient()

    handled = await run_command("/register 111", 999, repository, telegram_client)

    assert handled is True
    assert repository.users[111]["status"] == "active"
    assert repository.users[111]["onboarding_status"] == "pending"
    assert telegram_client.messages == [(1234, responses.USER_REGISTERED)]


async def test_admin_register_reactivates_inactive_user_without_deleting_data() -> None:
    repository = FakeUsersRepository()
    telegram_client = FakeTelegramClient()
    user = repository.create_registered_user(111, registered_by_telegram_id=999)
    user["status"] = "inactive"
    user["first_name"] = "Budi"
    user["last_name"] = "Santoso"

    await run_command("/register 111", 999, repository, telegram_client)

    assert repository.users[111]["status"] == "active"
    assert repository.users[111]["first_name"] == "Budi"
    assert repository.users[111]["last_name"] == "Santoso"
    assert repository.users[111]["unregistered_at"] is None
    assert telegram_client.messages == [(1234, responses.USER_REACTIVATED)]


async def test_admin_unregister_deactivates_user_and_refuses_self_unregister() -> None:
    repository = FakeUsersRepository()
    telegram_client = FakeTelegramClient()
    repository.create_registered_user(111, registered_by_telegram_id=999)

    await run_command("/unreg 111", 999, repository, telegram_client)
    await run_command("/unreg 999", 999, repository, telegram_client)

    assert repository.users[111]["status"] == "inactive"
    assert repository.users[111]["unregistered_at"] == "now"
    assert telegram_client.messages == [
        (1234, responses.USER_UNREGISTERED),
        (1234, responses.ADMIN_SELF_UNREGISTER_DENIED),
    ]


async def test_non_admin_admin_command_is_denied_and_does_not_change_data() -> None:
    repository = FakeUsersRepository()
    telegram_client = FakeTelegramClient()

    await run_command("/register 111", 555, repository, telegram_client)

    assert repository.users == {}
    assert telegram_client.messages == [(1234, responses.ACCESS_DENIED)]


async def test_admin_users_lists_active_inactive_and_missing_names() -> None:
    repository = FakeUsersRepository()
    telegram_client = FakeTelegramClient()
    named = repository.create_registered_user(111, registered_by_telegram_id=999)
    named["first_name"] = "Budi"
    named["last_name"] = "Santoso"
    missing_name = repository.create_registered_user(222, registered_by_telegram_id=999)
    missing_name["status"] = "inactive"

    await run_command("/users", 999, repository, telegram_client)

    assert telegram_client.messages == [
        (
            1234,
            "Daftar user terdaftar:\n\n"
            "1. 111 - Budi Santoso - active\n"
            "2. 222 - Belum isi nama - inactive",
        )
    ]


async def test_invalid_admin_command_format_returns_usage_response() -> None:
    repository = FakeUsersRepository()
    telegram_client = FakeTelegramClient()

    await run_command("/register", 999, repository, telegram_client)
    await run_command("/unreg abc", 999, repository, telegram_client)

    assert telegram_client.messages == [
        (1234, responses.INVALID_REGISTER_USAGE),
        (1234, responses.INVALID_TELEGRAM_ID),
    ]


async def test_telegram_webhook_accepts_update_and_returns_ok() -> None:
    repository = FakeUsersRepository()
    telegram_client = FakeTelegramClient()
    app.dependency_overrides[get_settings] = lambda: FakeSettings()
    app.dependency_overrides[get_users_repository] = lambda: repository
    app.dependency_overrides[get_transactions_repository] = FakeTransactionsRepository
    app.dependency_overrides[get_telegram_client] = lambda: telegram_client

    try:
        client = TestClient(app)
        response = client.post(
            "/webhooks/telegram",
            json={
                "update_id": 1,
                "message": {
                    "message_id": 1,
                    "text": "/register 111",
                    "from": {"id": 999},
                    "chat": {"id": 1234},
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert repository.users[111]["status"] == "active"
    assert telegram_client.messages == [(1234, responses.USER_REGISTERED)]


async def test_telegram_webhook_hides_processing_errors() -> None:
    app.dependency_overrides[get_settings] = lambda: FakeSettings()
    app.dependency_overrides[get_users_repository] = lambda: FakeUsersRepository()
    app.dependency_overrides[get_transactions_repository] = FakeTransactionsRepository
    app.dependency_overrides[get_telegram_client] = lambda: FailingTelegramClient()

    try:
        client = TestClient(app)
        response = client.post(
            "/webhooks/telegram",
            json={
                "update_id": 1,
                "message": {
                    "message_id": 1,
                    "text": "/users",
                    "from": {"id": 999},
                    "chat": {"id": 1234},
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"ok": True}
