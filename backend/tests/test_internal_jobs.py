from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.api.dependencies import get_conversation_states_repository, get_settings
from app.api.routes.internal import (
    get_pending_token_claims_repository,
    get_registration_tokens_repository,
    get_telegram_client,
)
from app.bot import responses
from app.bot.advisor import ADVISOR_MODE_STATE
from app.main import app
from app.repositories.conversation_states_repository import ConversationStatesRepository
from app.repositories.pending_token_claims_repository import (
    PendingTokenClaimsRepository,
)
from app.repositories.registration_tokens_repository import RegistrationTokensRepository
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


def _create_token_row(
    supabase: FakeSupabaseClient,
    token: str,
    expires_at: datetime,
    status: str = "active",
) -> None:
    supabase.tables.setdefault("registration_tokens", []).append(
        {
            "id": supabase.make_id(),
            "token": token,
            "created_by_telegram_id": 999,
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": expires_at.isoformat(),
            "claimed_at": None,
            "claimed_by_telegram_id": None,
            "claimed_user_id": None,
            "status": status,
        }
    )


def _create_pending_claim_row(
    supabase: FakeSupabaseClient,
    telegram_user_id: int,
    expires_at: datetime,
) -> None:
    supabase.tables.setdefault("pending_token_claims", []).append(
        {
            "id": supabase.make_id(),
            "telegram_user_id": telegram_user_id,
            "chat_id": 1234,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.now(UTC).isoformat(),
        }
    )


def test_expired_token_cleanup_job_rejects_missing_or_wrong_secret() -> None:
    app.dependency_overrides[get_settings] = lambda: FakeSettings()
    try:
        client = TestClient(app)

        missing = client.post("/internal/jobs/expired-token-cleanup")
        wrong = client.post(
            "/internal/jobs/expired-token-cleanup",
            headers={"X-Cron-Secret": "wrong"},
        )

        assert missing.status_code == 401
        assert wrong.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_expired_token_cleanup_job_accepts_secret_and_cleans() -> None:
    supabase = FakeSupabaseClient()
    tokens_repo = RegistrationTokensRepository(supabase)
    claims_repo = PendingTokenClaimsRepository(supabase)

    # Expired token (should be marked expired)
    _create_token_row(
        supabase,
        "EXPD-EXPD-EX01",
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    # Active token (should remain active)
    _create_token_row(
        supabase,
        "ACTV-ACTV-AC02",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    # Expired pending claim (should be deleted)
    _create_pending_claim_row(
        supabase,
        telegram_user_id=111,
        expires_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    # Active pending claim (should remain)
    _create_pending_claim_row(
        supabase,
        telegram_user_id=222,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )

    app.dependency_overrides[get_settings] = lambda: FakeSettings()
    app.dependency_overrides[get_registration_tokens_repository] = lambda: tokens_repo
    app.dependency_overrides[get_pending_token_claims_repository] = lambda: claims_repo
    try:
        client = TestClient(app)
        response = client.post(
            "/internal/jobs/expired-token-cleanup",
            headers={"X-Cron-Secret": "secret"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body == {"ok": True, "tokens_marked": 1, "claims_deleted": 1}

        # Verify the token was flipped to expired
        statuses = [row["status"] for row in supabase.tables["registration_tokens"]]
        assert statuses == ["expired", "active"]

        # Verify only the expired pending claim was deleted
        remaining_claims = [
            row["telegram_user_id"] for row in supabase.tables["pending_token_claims"]
        ]
        assert remaining_claims == [222]
    finally:
        app.dependency_overrides.clear()
