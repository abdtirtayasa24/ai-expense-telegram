from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.bot import responses
from app.bot.token_claim import (
    handle_token_claim,
    handle_token_claim_callback,
    token_claim_inline_keyboard,
)

pytestmark = pytest.mark.asyncio


class FakeUsersRepository:
    def __init__(self) -> None:
        self.users: dict[int, dict[str, Any]] = {}

    def get_by_telegram_user_id(self, telegram_user_id: int) -> dict[str, Any] | None:
        return self.users.get(telegram_user_id)


class FakePendingTokenClaimsRepository:
    def __init__(self) -> None:
        self.claims: dict[int, dict[str, Any]] = {}

    def upsert(
        self,
        telegram_user_id: int,
        chat_id: int,
        expires_at: datetime,
    ) -> dict[str, Any]:
        self.claims[telegram_user_id] = {
            "telegram_user_id": telegram_user_id,
            "chat_id": chat_id,
            "expires_at": expires_at.isoformat(),
        }
        return self.claims[telegram_user_id]

    def get_active(self, telegram_user_id: int) -> dict[str, Any] | None:
        claim = self.claims.get(telegram_user_id)
        if claim is None:
            return None
        expires_at = datetime.fromisoformat(claim["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            return None
        return claim

    def get_for_telegram_user_id(
        self,
        telegram_user_id: int,
    ) -> dict[str, Any] | None:
        return self.claims.get(telegram_user_id)

    def delete(self, telegram_user_id: int) -> bool:
        return self.claims.pop(telegram_user_id, None) is not None


class FakeRegistrationTokensRepository:
    def __init__(self) -> None:
        self.tokens: dict[str, dict[str, Any]] = {}
        self.claimed_tokens: list[dict[str, Any]] = []

    def claim(
        self,
        token: str,
        telegram_user_id: int,
        telegram_username: str | None = None,
        language_code: str = "id",
        currency: str = "IDR",
        timezone: str = "Asia/Jakarta",
    ) -> dict[str, Any]:
        from app.services.token_service import normalize_token

        normalized = normalize_token(token)
        for stored_token, row in self.tokens.items():
            if normalize_token(stored_token) == normalized:
                if row["status"] == "claimed":
                    return {"ok": False, "error": "already_claimed"}
                if row["expires_at"] < datetime.now(UTC):
                    row["status"] = "expired"
                    return {"ok": False, "error": "expired"}
                row["status"] = "claimed"
                row["claimed_at"] = datetime.now(UTC).isoformat()
                row["claimed_by_telegram_id"] = telegram_user_id
                claim_record = {
                    "token": token,
                    "telegram_user_id": telegram_user_id,
                }
                self.claimed_tokens.append(claim_record)
                return {"ok": True, "user_id": f"user-{telegram_user_id}"}
        return {"ok": False, "error": "not_found"}


class FakeTelegramClient:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str, dict | None]] = []
        self.callback_answers: list[tuple[str, str | None]] = []

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict | None = None,
    ) -> dict[str, bool]:
        self.messages.append((chat_id, text, reply_markup))
        return {"ok": True}

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str | None = None,
    ) -> dict[str, bool]:
        self.callback_answers.append((callback_query_id, text))
        return {"ok": True}


def _make_repos():
    return (
        FakeUsersRepository(),
        FakePendingTokenClaimsRepository(),
        FakeRegistrationTokensRepository(),
        FakeTelegramClient(),
    )


async def test_start_creates_pending_claim_and_sends_prompt_with_button() -> None:
    users, pending, tokens_repo, telegram = _make_repos()

    handled = await handle_token_claim(
        text="/start",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=users,
        pending_claims_repository=pending,
        registration_tokens_repository=tokens_repo,
        telegram_client=telegram,
        claim_timeout_minutes=10,
        admin_contact_telegram="@admin",
        admin_contact_whatsapp="08123",
    )

    assert handled is True
    assert 111 in pending.claims
    assert len(telegram.messages) == 1
    chat_id, text, reply_markup = telegram.messages[0]
    assert chat_id == 1234
    assert "belum terdaftar" in text.lower()
    assert reply_markup is not None
    assert "inline_keyboard" in reply_markup


async def test_active_user_is_not_intercepted_by_token_claim() -> None:
    users, pending, tokens_repo, telegram = _make_repos()
    users.users[111] = {"id": "user-111", "status": "active"}

    handled = await handle_token_claim(
        text="/start",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=users,
        pending_claims_repository=pending,
        registration_tokens_repository=tokens_repo,
        telegram_client=telegram,
        claim_timeout_minutes=10,
    )

    assert handled is False
    assert telegram.messages == []


async def test_no_pending_claim_and_not_start_returns_false() -> None:
    users, pending, tokens_repo, telegram = _make_repos()

    handled = await handle_token_claim(
        text="hello world",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=users,
        pending_claims_repository=pending,
        registration_tokens_repository=tokens_repo,
        telegram_client=telegram,
        claim_timeout_minutes=10,
    )

    assert handled is False
    assert telegram.messages == []


async def test_valid_token_claims_and_sends_success() -> None:
    users, pending, tokens_repo, telegram = _make_repos()
    tokens_repo.tokens["K7M2-PQ9X-AB43"] = {
        "status": "active",
        "expires_at": datetime.now(UTC) + timedelta(days=30),
    }
    # Simulate the user having a pending claim (from /start)
    pending.upsert(111, 1234, datetime.now(UTC) + timedelta(minutes=10))

    handled = await handle_token_claim(
        text="k7m2-pq9x-ab43",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=users,
        pending_claims_repository=pending,
        registration_tokens_repository=tokens_repo,
        telegram_client=telegram,
        claim_timeout_minutes=10,
    )

    assert handled is True
    assert 111 not in pending.claims  # pending claim was deleted
    assert len(telegram.messages) == 1
    assert telegram.messages[0][1] == responses.TOKEN_CLAIM_ACTIVE
    assert tokens_repo.tokens["K7M2-PQ9X-AB43"]["status"] == "claimed"


async def test_invalid_token_format_keeps_pending_claim() -> None:
    users, pending, tokens_repo, telegram = _make_repos()
    pending.upsert(111, 1234, datetime.now(UTC) + timedelta(minutes=10))

    handled = await handle_token_claim(
        text="this is not a token",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=users,
        pending_claims_repository=pending,
        registration_tokens_repository=tokens_repo,
        telegram_client=telegram,
        claim_timeout_minutes=10,
    )

    assert handled is True
    assert 111 in pending.claims  # still active for retry
    assert len(telegram.messages) == 1
    assert "kirimkan tokennya" in telegram.messages[0][1].lower()


async def test_token_not_found_keeps_pending_claim_for_retry() -> None:
    users, pending, tokens_repo, telegram = _make_repos()
    pending.upsert(111, 1234, datetime.now(UTC) + timedelta(minutes=10))

    handled = await handle_token_claim(
        text="ZZZZ-ZZZZ-ZZZZ",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=users,
        pending_claims_repository=pending,
        registration_tokens_repository=tokens_repo,
        telegram_client=telegram,
        claim_timeout_minutes=10,
    )

    assert handled is True
    assert 111 in pending.claims  # still active for retry
    assert telegram.messages[0][1] == responses.TOKEN_INVALID


async def test_expired_token_sends_expired_message() -> None:
    users, pending, tokens_repo, telegram = _make_repos()
    tokens_repo.tokens["EXPD-EXPD-EX01"] = {
        "status": "active",
        "expires_at": datetime.now(UTC) - timedelta(days=1),
    }
    pending.upsert(111, 1234, datetime.now(UTC) + timedelta(minutes=10))

    handled = await handle_token_claim(
        text="EXPD-EXPD-EX01",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=users,
        pending_claims_repository=pending,
        registration_tokens_repository=tokens_repo,
        telegram_client=telegram,
        claim_timeout_minutes=10,
    )

    assert handled is True
    assert telegram.messages[0][1] == responses.TOKEN_EXPIRED


async def test_already_claimed_token_sends_claimed_message() -> None:
    users, pending, tokens_repo, telegram = _make_repos()
    tokens_repo.tokens["CM7D-CM7D-CM01"] = {
        "status": "claimed",
        "expires_at": datetime.now(UTC) + timedelta(days=30),
        "claimed_at": datetime.now(UTC).isoformat(),
    }
    pending.upsert(111, 1234, datetime.now(UTC) + timedelta(minutes=10))

    handled = await handle_token_claim(
        text="CM7D-CM7D-CM01",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=users,
        pending_claims_repository=pending,
        registration_tokens_repository=tokens_repo,
        telegram_client=telegram,
        claim_timeout_minutes=10,
    )

    assert handled is True
    assert telegram.messages[0][1] == responses.TOKEN_ALREADY_CLAIMED


async def test_pending_claim_expired_prompts_restart_and_deletes_claim() -> None:
    users, pending, tokens_repo, telegram = _make_repos()
    pending.claims[111] = {
        "telegram_user_id": 111,
        "chat_id": 1234,
        "expires_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
    }

    handled = await handle_token_claim(
        text="K7M2-PQ9X-AB43",
        telegram_user_id=111,
        chat_id=1234,
        users_repository=users,
        pending_claims_repository=pending,
        registration_tokens_repository=tokens_repo,
        telegram_client=telegram,
        claim_timeout_minutes=10,
    )

    assert handled is True
    assert 111 not in pending.claims
    assert telegram.messages[0][1] == responses.TOKEN_PROMPT_EXPIRED


async def test_callback_refreshes_pending_claim_and_prompts() -> None:
    pending = FakePendingTokenClaimsRepository()
    telegram = FakeTelegramClient()

    handled = await handle_token_claim_callback(
        callback_query_id="cb-1",
        telegram_user_id=111,
        chat_id=1234,
        pending_claims_repository=pending,
        telegram_client=telegram,
        claim_timeout_minutes=10,
    )

    assert handled is True
    assert 111 in pending.claims
    assert len(telegram.callback_answers) == 1
    assert telegram.callback_answers[0] == (
        "cb-1",
        "Silakan kirim token pendaftaran kamu.",
    )
    assert len(telegram.messages) == 1


async def test_inline_keyboard_has_token_button() -> None:
    keyboard = token_claim_inline_keyboard()
    assert "inline_keyboard" in keyboard
    button = keyboard["inline_keyboard"][0][0]
    assert button["text"] == responses.TOKEN_PROMPT_BUTTON
    assert button["callback_data"] == "token_claim"