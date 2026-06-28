from decimal import Decimal
from typing import Any

import pytest

from app.bot import responses
from app.bot.onboarding import handle_registered_user_message, is_valid_name
from app.bot.webhook import process_telegram_message
from app.services.rule_parser import today_jakarta

pytestmark = pytest.mark.asyncio


class FakeUsersRepository:
    def __init__(self) -> None:
        self.users: dict[int, dict[str, Any]] = {}

    def add_user(
        self,
        telegram_user_id: int,
        status: str = "active",
        onboarding_status: str = "pending",
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> dict[str, Any]:
        row = {
            "id": f"user-{telegram_user_id}",
            "telegram_user_id": telegram_user_id,
            "status": status,
            "onboarding_status": onboarding_status,
            "first_name": first_name,
            "last_name": last_name,
        }
        self.users[telegram_user_id] = row
        return row

    def get_by_telegram_user_id(self, telegram_user_id: int) -> dict[str, Any] | None:
        return self.users.get(telegram_user_id)

    def update_profile(
        self,
        user_id: str,
        first_name: str | None = None,
        last_name: str | None = None,
        telegram_username: str | None = None,
    ) -> dict[str, Any] | None:
        row = self._get_by_id(user_id)
        if row is None:
            return None
        if first_name is not None:
            row["first_name"] = first_name
        if last_name is not None:
            row["last_name"] = last_name
        if telegram_username is not None:
            row["telegram_username"] = telegram_username
        return row

    def update_onboarding_status(
        self,
        user_id: str,
        onboarding_status: str,
    ) -> dict[str, Any] | None:
        row = self._get_by_id(user_id)
        if row is None:
            return None
        row["onboarding_status"] = onboarding_status
        return row

    def list_users(self) -> list[dict[str, Any]]:
        return list(self.users.values())

    def _get_by_id(self, user_id: str) -> dict[str, Any] | None:
        return next(
            (row for row in self.users.values() if row["id"] == user_id),
            None,
        )


class StaleFirstReadUsersRepository(FakeUsersRepository):
    def __init__(self) -> None:
        super().__init__()
        self.read_count = 0

    def get_by_telegram_user_id(self, telegram_user_id: int) -> dict[str, Any] | None:
        user = super().get_by_telegram_user_id(telegram_user_id)
        if user is None:
            return None
        self.read_count += 1
        if self.read_count == 1:
            stale_user = dict(user)
            stale_user["first_name"] = None
            return stale_user
        return user


class FakeTransactionsRepository:
    def __init__(self) -> None:
        self.transactions: list[dict[str, Any]] = []

    def create(self, **payload: Any) -> dict[str, Any]:
        row = {"id": f"tx-{len(self.transactions) + 1}", **payload}
        self.transactions.append(row)
        return row


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


async def test_missing_or_inactive_users_are_rejected() -> None:
    repository = FakeUsersRepository()
    telegram_client = FakeTelegramClient()
    repository.add_user(222, status="inactive")

    missing_allowed = await handle_registered_user_message(
        text="Halo",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=repository,  # type: ignore[arg-type]
        telegram_client=telegram_client,
        transactions_repository=FakeTransactionsRepository(),
        parser_confidence_threshold=0.75,
        admin_contact_telegram="@admin",
        admin_contact_whatsapp="08123",
    )
    inactive_allowed = await handle_registered_user_message(
        text="Halo",
        telegram_user_id=222,
        chat_id=1234,
        users_repository=repository,  # type: ignore[arg-type]
        telegram_client=telegram_client,
        transactions_repository=FakeTransactionsRepository(),
        parser_confidence_threshold=0.75,
        admin_contact_telegram="@admin",
        admin_contact_whatsapp="08123",
    )

    assert missing_allowed is False
    assert inactive_allowed is False
    assert telegram_client.messages == [
        (1234, responses.user_not_active_with_contact(111, "@admin", "08123")),
        (1234, responses.user_not_active_with_contact(222, "@admin", "08123")),
    ]


async def test_pending_user_is_asked_for_first_name() -> None:
    repository = FakeUsersRepository()
    telegram_client = FakeTelegramClient()
    user = repository.add_user(111, onboarding_status="pending")

    allowed = await handle_registered_user_message(
        text="/start",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=repository,  # type: ignore[arg-type]
        telegram_client=telegram_client,
        transactions_repository=FakeTransactionsRepository(),
        parser_confidence_threshold=0.75,
    )

    assert allowed is False
    assert user["onboarding_status"] == "asking_first_name"
    assert telegram_client.messages == [(1234, responses.ASK_FIRST_NAME)]


async def test_first_name_is_validated_saved_and_moves_to_last_name() -> None:
    repository = FakeUsersRepository()
    telegram_client = FakeTelegramClient()
    user = repository.add_user(111, onboarding_status="asking_first_name")

    invalid_allowed = await handle_registered_user_message(
        text="B1",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=repository,  # type: ignore[arg-type]
        telegram_client=telegram_client,
        transactions_repository=FakeTransactionsRepository(),
        parser_confidence_threshold=0.75,
    )
    valid_allowed = await handle_registered_user_message(
        text="Budi",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=repository,  # type: ignore[arg-type]
        telegram_client=telegram_client,
        transactions_repository=FakeTransactionsRepository(),
        parser_confidence_threshold=0.75,
    )

    assert invalid_allowed is False
    assert valid_allowed is False
    assert user["first_name"] == "Budi"
    assert user["onboarding_status"] == "asking_last_name"
    assert telegram_client.messages == [
        (1234, responses.INVALID_NAME),
        (1234, responses.ASK_LAST_NAME),
    ]


async def test_last_name_is_validated_saved_and_completes_onboarding() -> None:
    repository = FakeUsersRepository()
    telegram_client = FakeTelegramClient()
    user = repository.add_user(
        111,
        onboarding_status="asking_last_name",
        first_name="Budi",
    )

    invalid_allowed = await handle_registered_user_message(
        text="S@",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=repository,  # type: ignore[arg-type]
        telegram_client=telegram_client,
        transactions_repository=FakeTransactionsRepository(),
        parser_confidence_threshold=0.75,
    )
    valid_allowed = await handle_registered_user_message(
        text="Santoso",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=repository,  # type: ignore[arg-type]
        telegram_client=telegram_client,
        transactions_repository=FakeTransactionsRepository(),
        parser_confidence_threshold=0.75,
    )

    assert invalid_allowed is False
    assert valid_allowed is True
    assert user["last_name"] == "Santoso"
    assert user["onboarding_status"] == "completed"
    assert telegram_client.messages == [
        (1234, responses.INVALID_NAME),
        (1234, responses.onboarding_completed("Budi")),
    ]


async def test_completion_message_uses_refetched_first_name() -> None:
    repository = StaleFirstReadUsersRepository()
    telegram_client = FakeTelegramClient()
    repository.add_user(
        111,
        onboarding_status="asking_last_name",
        first_name="Budi",
    )

    allowed = await handle_registered_user_message(
        text="Santoso",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=repository,  # type: ignore[arg-type]
        telegram_client=telegram_client,
        transactions_repository=FakeTransactionsRepository(),
        parser_confidence_threshold=0.75,
    )

    assert allowed is True
    assert telegram_client.messages == [
        (1234, responses.onboarding_completed("Budi"))
    ]


async def test_completed_user_saves_expense_transaction_payload() -> None:
    repository = FakeUsersRepository()
    transactions_repository = FakeTransactionsRepository()
    telegram_client = FakeTelegramClient()
    repository.add_user(
        111,
        onboarding_status="completed",
        first_name="Budi",
        last_name="Santoso",
    )

    allowed = await handle_registered_user_message(
        text="Bayar parkir 5000",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=repository,  # type: ignore[arg-type]
        telegram_client=telegram_client,
        transactions_repository=transactions_repository,
        parser_confidence_threshold=0.75,
    )

    assert allowed is True
    assert transactions_repository.transactions == [
        {
            "id": "tx-1",
            "user_id": "user-111",
            "transaction_type": "expense",
            "name": "Parkir",
            "category": "transportasi",
            "amount": Decimal("5000"),
            "transaction_date": today_jakarta(),
            "source": "telegram_chat",
            "parser": "rule_based",
            "confidence_score": 1.0,
            "raw_message": "Bayar parkir 5000",
        }
    ]
    assert telegram_client.messages == [
        (1234, "Oke, pengeluaran parkir Rp5.000 sudah tercatat.")
    ]


async def test_completed_user_saves_income_transaction() -> None:
    repository = FakeUsersRepository()
    transactions_repository = FakeTransactionsRepository()
    telegram_client = FakeTelegramClient()
    repository.add_user(111, onboarding_status="completed")

    allowed = await handle_registered_user_message(
        text="Gaji masuk 8000000",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=repository,  # type: ignore[arg-type]
        telegram_client=telegram_client,
        transactions_repository=transactions_repository,
        parser_confidence_threshold=0.75,
    )

    assert allowed is True
    assert transactions_repository.transactions[0]["transaction_type"] == "income"
    assert transactions_repository.transactions[0]["amount"] == Decimal("8000000")
    assert telegram_client.messages == [
        (1234, "Oke, pemasukan transaksi Rp8.000.000 sudah tercatat.")
    ]


async def test_low_confidence_parse_asks_clarification_without_saving() -> None:
    repository = FakeUsersRepository()
    transactions_repository = FakeTransactionsRepository()
    telegram_client = FakeTelegramClient()
    repository.add_user(111, onboarding_status="completed")

    allowed = await handle_registered_user_message(
        text="Parkir 5000",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=repository,  # type: ignore[arg-type]
        telegram_client=telegram_client,
        transactions_repository=transactions_repository,
        parser_confidence_threshold=0.75,
    )

    assert allowed is False
    assert transactions_repository.transactions == []
    # Parser's clarification question or fallback should be sent
    assert len(telegram_client.messages) == 1
    chat_id, message = telegram_client.messages[0]
    assert chat_id == 1234
    assert "belum yakin" in message.lower()


async def test_incomplete_onboarding_does_not_create_transaction() -> None:
    repository = FakeUsersRepository()
    transactions_repository = FakeTransactionsRepository()
    telegram_client = FakeTelegramClient()
    repository.add_user(111, onboarding_status="pending")

    allowed = await handle_registered_user_message(
        text="Bayar parkir 5000",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=repository,  # type: ignore[arg-type]
        telegram_client=telegram_client,
        transactions_repository=transactions_repository,
        parser_confidence_threshold=0.75,
    )

    assert allowed is False
    assert transactions_repository.transactions == []
    assert telegram_client.messages == [(1234, responses.ASK_FIRST_NAME)]


async def test_negative_amount_is_rejected_without_saving() -> None:
    repository = FakeUsersRepository()
    transactions_repository = FakeTransactionsRepository()
    telegram_client = FakeTelegramClient()
    repository.add_user(111, onboarding_status="completed")

    # Parser might return negative amount for refund-like scenarios
    # Test that such amounts are rejected and clarification is asked
    allowed = await handle_registered_user_message(
        text="Refund -5000",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=repository,  # type: ignore[arg-type]
        telegram_client=telegram_client,
        transactions_repository=transactions_repository,
        parser_confidence_threshold=0.75,
    )

    assert allowed is False
    assert transactions_repository.transactions == []


async def test_admin_command_does_not_run_onboarding() -> None:
    repository = FakeUsersRepository()
    telegram_client = FakeTelegramClient()
    user = repository.add_user(999, onboarding_status="pending")

    await process_telegram_message(
        text="/users",
        sender_telegram_user_id=999,
        chat_id=1234,
        admin_telegram_id=999,
        users_repository=repository,  # type: ignore[arg-type]
        transactions_repository=FakeTransactionsRepository(),  # type: ignore[arg-type]
        telegram_client=telegram_client,  # type: ignore[arg-type]
        parser_confidence_threshold=0.75,
    )

    assert user["onboarding_status"] == "pending"
    assert telegram_client.messages == [
        (1234, "Daftar user terdaftar:\n\n1. 999 - Belum isi nama - active")
    ]


async def test_name_validation_accepts_allowed_characters_only() -> None:
    assert is_valid_name("Siti Aminah") is True
    assert is_valid_name("D'Angelo") is True
    assert is_valid_name("Anne-Marie") is True
    assert is_valid_name("A") is False
    assert is_valid_name("Budi1") is False
    assert is_valid_name("Budi_") is False
