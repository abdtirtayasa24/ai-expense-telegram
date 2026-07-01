from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.repositories.pending_token_claims_repository import (
    PendingTokenClaimsRepository,
)
from app.repositories.registration_tokens_repository import (
    CLAIM_ERROR_ALREADY_CLAIMED,
    CLAIM_ERROR_EXPIRED,
    CLAIM_ERROR_NOT_FOUND,
    RegistrationTokensRepository,
)
from tests.test_repositories import FakeSupabaseClient


def _create_token_row(
    client: FakeSupabaseClient,
    token: str,
    expires_at: datetime,
    created_by: int = 999,
    status: str = "active",
) -> dict:
    client.tables.setdefault("registration_tokens", []).append(
        {
            "id": client.make_id(),
            "token": token,
            "created_by_telegram_id": created_by,
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": expires_at.isoformat(),
            "claimed_at": None,
            "claimed_by_telegram_id": None,
            "claimed_user_id": None,
            "status": status,
        }
    )
    return client.tables["registration_tokens"][-1]


def test_registration_tokens_create_and_get_by_token() -> None:
    client = FakeSupabaseClient()
    repo = RegistrationTokensRepository(client)

    created = repo.create(
        token="K7M2-PQ9X-AB43",
        expires_at=datetime.now(UTC) + timedelta(days=30),
        created_by_telegram_id=999,
    )
    assert created["token"] == "K7M2-PQ9X-AB43"
    assert created["status"] == "active"

    fetched = repo.get_by_token("k7m2pq9xab43")
    assert fetched is not None
    assert fetched["id"] == created["id"]


def test_registration_tokens_create_batch_generates_unique_tokens() -> None:
    client = FakeSupabaseClient()
    repo = RegistrationTokensRepository(client)

    rows = repo.create_batch(
        count=5,
        expires_at=datetime.now(UTC) + timedelta(days=30),
        created_by_telegram_id=999,
    )
    assert len(rows) == 5
    assert len({row["token"] for row in rows}) == 5


def test_registration_tokens_claim_success_creates_user() -> None:
    client = FakeSupabaseClient()
    repo = RegistrationTokensRepository(client)
    _create_token_row(
        client,
        "K7M2-PQ9X-AB43",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    result = repo.claim(
        token="k7m2-pq9x-ab43",
        telegram_user_id=111,
        telegram_username="budi",
    )

    assert result["ok"] is True
    assert "user_id" in result
    users = client.tables.get("users", [])
    assert len(users) == 1
    assert users[0]["telegram_user_id"] == 111
    assert users[0]["status"] == "active"
    assert users[0]["onboarding_status"] == "pending"

    token_row = client.tables["registration_tokens"][0]
    assert token_row["status"] == "claimed"
    assert token_row["claimed_at"] is not None
    assert token_row["claimed_by_telegram_id"] == 111


def test_registration_tokens_claim_reactivates_existing_inactive_user() -> None:
    client = FakeSupabaseClient()
    repo = RegistrationTokensRepository(client)
    _create_token_row(
        client,
        "K7M2-PQ9X-AB43",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    client.tables.setdefault("users", []).append(
        {
            "id": "existing-user",
            "telegram_user_id": 111,
            "telegram_username": None,
            "role": "user",
            "status": "inactive",
            "onboarding_status": "completed",
            "first_name": "Budi",
            "last_name": "Santoso",
            "unregistered_at": datetime.now(UTC).isoformat(),
        }
    )

    result = repo.claim(
        token="K7M2-PQ9X-AB43",
        telegram_user_id=111,
        telegram_username="budi",
    )

    assert result == {"ok": True, "user_id": "existing-user"}
    users = client.tables["users"]
    assert len(users) == 1
    assert users[0]["status"] == "active"
    assert users[0]["onboarding_status"] == "pending"
    assert users[0]["unregistered_at"] is None
    assert client.tables["registration_tokens"][0]["status"] == "claimed"
    assert client.tables["registration_tokens"][0]["claimed_user_id"] == "existing-user"


def test_registration_tokens_claim_active_existing_user_does_not_claim_token() -> None:
    client = FakeSupabaseClient()
    repo = RegistrationTokensRepository(client)
    _create_token_row(
        client,
        "K7M2-PQ9X-AB43",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    client.tables.setdefault("users", []).append(
        {
            "id": "existing-user",
            "telegram_user_id": 111,
            "status": "active",
            "onboarding_status": "completed",
        }
    )

    result = repo.claim(token="K7M2-PQ9X-AB43", telegram_user_id=111)

    assert result == {"ok": False, "error": "already_registered"}
    assert client.tables["registration_tokens"][0]["status"] == "active"
    assert client.tables["registration_tokens"][0]["claimed_at"] is None


def test_registration_tokens_claim_not_found() -> None:
    client = FakeSupabaseClient()
    repo = RegistrationTokensRepository(client)

    result = repo.claim(
        token="ZZZZ-ZZZZ-ZZZZ",
        telegram_user_id=111,
    )
    assert result["ok"] is False
    assert result["error"] == CLAIM_ERROR_NOT_FOUND


def test_registration_tokens_claim_already_claimed() -> None:
    client = FakeSupabaseClient()
    repo = RegistrationTokensRepository(client)
    _create_token_row(
        client,
        "K7M2-PQ9X-AB43",
        expires_at=datetime.now(UTC) + timedelta(days=30),
        status="claimed",
    )
    # Simulate already claimed
    client.tables["registration_tokens"][0]["claimed_at"] = datetime.now(
        UTC
    ).isoformat()

    result = repo.claim(
        token="K7M2-PQ9X-AB43",
        telegram_user_id=111,
    )
    assert result["ok"] is False
    assert result["error"] == CLAIM_ERROR_ALREADY_CLAIMED


def test_registration_tokens_claim_expired_marks_status_and_returns_error() -> None:
    client = FakeSupabaseClient()
    repo = RegistrationTokensRepository(client)
    _create_token_row(
        client,
        "K7M2-PQ9X-AB43",
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )

    result = repo.claim(
        token="K7M2-PQ9X-AB43",
        telegram_user_id=111,
    )
    assert result["ok"] is False
    assert result["error"] == CLAIM_ERROR_EXPIRED
    assert client.tables["registration_tokens"][0]["status"] == "expired"


def test_registration_tokens_mark_expired_flips_active_past_expiry() -> None:
    client = FakeSupabaseClient()
    repo = RegistrationTokensRepository(client)
    _create_token_row(
        client,
        "EXPD-EXPD-EX01",
        expires_at=datetime.now(UTC) - timedelta(days=2),
    )
    _create_token_row(
        client,
        "EXP2-EXP2-EX02",
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    _create_token_row(
        client,
        "ACTV-ACTV-AC02",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    count = repo.mark_expired(limit=1)
    assert count == 1
    statuses = [row["status"] for row in client.tables["registration_tokens"]]
    assert statuses == ["expired", "active", "active"]


def test_pending_token_claims_upsert_get_active_and_delete() -> None:
    client = FakeSupabaseClient()
    repo = PendingTokenClaimsRepository(client)

    expires = datetime.now(UTC) + timedelta(minutes=10)
    claim = repo.upsert(telegram_user_id=111, chat_id=1234, expires_at=expires)
    assert claim["telegram_user_id"] == 111

    active = repo.get_active(111)
    assert active is not None
    assert active["chat_id"] == 1234

    # Upsert refreshes the existing row instead of duplicating
    repo.upsert(
        telegram_user_id=111,
        chat_id=5678,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    assert len(client.tables["pending_token_claims"]) == 1
    assert client.tables["pending_token_claims"][0]["chat_id"] == 5678

    assert repo.delete(111) is True
    assert repo.get_active(111) is None


def test_pending_token_claims_get_active_returns_none_for_expired() -> None:
    client = FakeSupabaseClient()
    repo = PendingTokenClaimsRepository(client)

    repo.upsert(
        telegram_user_id=111,
        chat_id=1234,
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    assert repo.get_active(111) is None


def test_pending_token_claims_delete_expired_via_rpc() -> None:
    client = FakeSupabaseClient()
    repo = PendingTokenClaimsRepository(client)

    repo.upsert(
        telegram_user_id=111,
        chat_id=1234,
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    repo.upsert(
        telegram_user_id=222,
        chat_id=5678,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )

    repo.upsert(
        telegram_user_id=333,
        chat_id=9012,
        expires_at=datetime.now(UTC) - timedelta(minutes=2),
    )

    count = repo.delete_expired(limit=1)
    assert count == 1
    remaining_user_ids = [
        row["telegram_user_id"] for row in client.tables["pending_token_claims"]
    ]
    assert remaining_user_ids == [111, 222]