from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bot import responses
from app.bot.advisor import ADVISOR_MODE_STATE, handle_advisor_mode_message
from app.repositories.advisor_chat_repository import AdvisorChatRepository
from app.repositories.budgets_repository import BudgetsRepository
from app.repositories.conversation_states_repository import ConversationStatesRepository
from app.repositories.transactions_repository import TransactionsRepository
from app.services.advisor_chat_service import answer_advisor_question
from app.services.advisor_mode_timeout_service import notify_expired_advisor_modes
from tests.test_repositories import FakeSupabaseClient

pytestmark = pytest.mark.asyncio

_FAKE_ENV = {
    "APP_BASE_URL": "https://api.example.com",
    "MINI_APP_URL": "https://app.example.com",
    "TELEGRAM_BOT_TOKEN": "test-token",
    "ADMIN_TELEGRAM_ID": "999",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "test-key",
    "GEMINI_API_KEY": "test-gemini-key",
    "GEMINI_MODEL": "gemini-2.5-flash",
    "JWT_SECRET_KEY": "test-jwt-secret",
}


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


@patch.dict("os.environ", _FAKE_ENV)
@patch("google.genai.Client")
async def test_advisor_mode_stores_telegram_question_and_answer(
    mock_client_cls: MagicMock,
) -> None:
    client = FakeSupabaseClient()
    states = ConversationStatesRepository(client)
    chats = AdvisorChatRepository(client)
    telegram = FakeTelegramClient()
    user: dict[str, Any] = {"id": "user-1"}

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Pengeluaran bulan ini Rp0 karena belum ada data."
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    mock_client_cls.return_value = mock_client

    activated = await handle_advisor_mode_message(
        text="/advisor",
        user=user,
        chat_id=1234,
        telegram_client=telegram,
        transactions_repository=TransactionsRepository(client),
        budgets_repository=BudgetsRepository(client),
        conversation_states_repository=states,
        advisor_chat_repository=chats,
        gemini_api_key="test-key",
        gemini_model="test-model",
        timeout_minutes=15,
        history_limit=60,
    )
    answered = await handle_advisor_mode_message(
        text="Berapa pengeluaran saya bulan ini?",
        user=user,
        chat_id=1234,
        telegram_client=telegram,
        transactions_repository=TransactionsRepository(client),
        budgets_repository=BudgetsRepository(client),
        conversation_states_repository=states,
        advisor_chat_repository=chats,
        gemini_api_key="test-key",
        gemini_model="test-model",
        timeout_minutes=15,
        history_limit=60,
    )

    assert activated is True
    assert answered is True
    assert telegram.messages == [
        (1234, responses.ADVISOR_MODE_ACTIVE),
        (1234, "Pengeluaran bulan ini Rp0 karena belum ada data."),
    ]
    rows = client.tables["advisor_chat_messages"]
    assert [(row["role"], row["source"]) for row in rows] == [
        ("user", "telegram_chat"),
        ("assistant", "telegram_chat"),
    ]


@patch("app.services.advisor_chat_service.generate_chat_answer")
async def test_failed_advisor_answer_does_not_store_partial_history(
    mock_generate_answer: AsyncMock,
) -> None:
    client = FakeSupabaseClient()
    chats = AdvisorChatRepository(client)
    mock_generate_answer.side_effect = RuntimeError("Gemini unavailable")

    with pytest.raises(RuntimeError):
        await answer_advisor_question(
            user_id="user-1",
            message="Berapa pengeluaran saya?",
            source="mini_app",
            transactions_repository=TransactionsRepository(client),
            budgets_repository=BudgetsRepository(client),
            advisor_chat_repository=chats,
            api_key="test-key",
            model="test-model",
            history_limit=60,
        )

    assert client.tables.get("advisor_chat_messages", []) == []


async def test_transaction_command_exits_advisor_mode() -> None:
    client = FakeSupabaseClient()
    states = ConversationStatesRepository(client)
    telegram = FakeTelegramClient()
    user: dict[str, Any] = {"id": "user-1"}
    states.create(
        user_id="user-1",
        state=ADVISOR_MODE_STATE,
        payload={"chat_id": 1234},
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )

    handled = await handle_advisor_mode_message(
        text="/transaction",
        user=user,
        chat_id=1234,
        telegram_client=telegram,
        transactions_repository=TransactionsRepository(client),
        budgets_repository=BudgetsRepository(client),
        conversation_states_repository=states,
        advisor_chat_repository=AdvisorChatRepository(client),
        gemini_api_key="test-key",
        gemini_model="test-model",
        timeout_minutes=15,
        history_limit=60,
    )

    assert handled is True
    assert states.get_latest_for_user("user-1", ADVISOR_MODE_STATE) is None
    assert telegram.messages == [(1234, responses.TRANSACTION_MODE_ACTIVE)]


async def test_expired_advisor_modes_are_notified_and_deleted() -> None:
    client = FakeSupabaseClient()
    states = ConversationStatesRepository(client)
    telegram = FakeTelegramClient()
    states.create(
        user_id="user-1",
        state=ADVISOR_MODE_STATE,
        payload={"chat_id": 1234},
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )

    notified = await notify_expired_advisor_modes(states, telegram)  # type: ignore[arg-type]

    assert notified == 1
    assert states.get_latest_for_user("user-1", ADVISOR_MODE_STATE) is None
    assert telegram.messages == [(1234, responses.ADVISOR_MODE_TIMEOUT_NOTICE)]


async def test_advisor_chat_repository_lists_recent_messages_oldest_to_newest() -> None:
    client = FakeSupabaseClient()
    repository = AdvisorChatRepository(client)
    for index in range(3):
        row = repository.create_message(
            user_id="user-1",
            role="user",
            content=f"message-{index}",
            source="mini_app",
        )
        row["created_at"] = f"2026-06-27T00:0{index}:00+00:00"
        client.tables["advisor_chat_messages"][index]["created_at"] = row["created_at"]

    rows = repository.list_recent_for_user("user-1", limit=2)

    assert [row["content"] for row in rows] == ["message-1", "message-2"]
