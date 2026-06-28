from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.api.dependencies import get_conversation_states_repository, get_settings
from app.api.routes.internal import get_telegram_client
from app.bot import responses
from app.bot.advisor import ADVISOR_MODE_STATE
from app.main import app
from app.repositories.conversation_states_repository import ConversationStatesRepository
from tests.test_repositories import FakeSupabaseClient


@dataclass
class FakeSettings:
    telegram_bot_token: str = "test-token"
    cron_secret: str | None = "secret"


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


def test_advisor_mode_timeouts_job_rejects_missing_or_wrong_secret() -> None:
    app.dependency_overrides[get_settings] = lambda: FakeSettings()
    try:
        client = TestClient(app)

        missing = client.post("/internal/jobs/advisor-mode-timeouts")
        wrong = client.post(
            "/internal/jobs/advisor-mode-timeouts",
            headers={"X-Cron-Secret": "wrong"},
        )

        assert missing.status_code == 401
        assert wrong.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_advisor_mode_timeouts_job_accepts_secret_and_notifies() -> None:
    supabase = FakeSupabaseClient()
    states = ConversationStatesRepository(supabase)
    telegram = FakeTelegramClient()
    states.create(
        user_id="user-1",
        state=ADVISOR_MODE_STATE,
        payload={"chat_id": 1234},
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )

    app.dependency_overrides[get_settings] = lambda: FakeSettings()
    app.dependency_overrides[get_conversation_states_repository] = lambda: states
    app.dependency_overrides[get_telegram_client] = lambda: telegram
    try:
        client = TestClient(app)
        response = client.post(
            "/internal/jobs/advisor-mode-timeouts",
            headers={"X-Cron-Secret": "secret"},
        )

        assert response.status_code == 200
        assert response.json() == {"ok": True, "notified": 1}
        assert telegram.messages == [(1234, responses.ADVISOR_MODE_TIMEOUT_NOTICE)]
    finally:
        app.dependency_overrides.clear()


def test_advisor_mode_timeouts_job_does_not_notify_stale_expired_state() -> None:
    supabase = FakeSupabaseClient()
    states = ConversationStatesRepository(supabase)
    telegram = FakeTelegramClient()
    states.create(
        user_id="user-1",
        state=ADVISOR_MODE_STATE,
        payload={"chat_id": 1234},
        expires_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    states.create(
        user_id="user-1",
        state=ADVISOR_MODE_STATE,
        payload={"chat_id": 1234},
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )

    app.dependency_overrides[get_settings] = lambda: FakeSettings()
    app.dependency_overrides[get_conversation_states_repository] = lambda: states
    app.dependency_overrides[get_telegram_client] = lambda: telegram
    try:
        client = TestClient(app)
        response = client.post(
            "/internal/jobs/advisor-mode-timeouts",
            headers={"X-Cron-Secret": "secret"},
        )

        assert response.status_code == 200
        assert response.json() == {"ok": True, "notified": 0}
        assert telegram.messages == []
    finally:
        app.dependency_overrides.clear()
