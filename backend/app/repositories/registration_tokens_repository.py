from datetime import datetime
from typing import Any

from app.repositories.base import BaseRepository, Row
from app.services.token_service import format_token

CLAIM_OK = "ok"
CLAIM_ERROR_NOT_FOUND = "not_found"
CLAIM_ERROR_ALREADY_CLAIMED = "already_claimed"
CLAIM_ERROR_EXPIRED = "expired"


class RegistrationTokensRepository(BaseRepository):
    table_name = "registration_tokens"

    def create(
        self,
        token: str,
        expires_at: datetime,
        created_by_telegram_id: int | None = None,
    ) -> Row:
        payload = {
            "token": format_token(token),
            "expires_at": expires_at.isoformat(),
            "created_by_telegram_id": created_by_telegram_id,
            "status": "active",
        }
        result = self.table().insert(payload).execute()
        row = self.first(result)
        if row is None:
            raise RuntimeError(
                "Supabase did not return the created registration token."
            )
        return row

    def create_batch(
        self,
        count: int,
        expires_at: datetime,
        created_by_telegram_id: int | None = None,
    ) -> list[Row]:
        from app.services.token_service import generate_token

        rows: list[Row] = []
        for _ in range(count):
            rows.append(
                self.create(
                    token=generate_token(),
                    expires_at=expires_at,
                    created_by_telegram_id=created_by_telegram_id,
                )
            )
        return rows

    def get_by_token(self, token: str) -> Row | None:
        result = (
            self.table()
            .select("*")
            .eq("token", format_token(token))
            .limit(1)
            .execute()
        )
        return self.first(result)

    def claim(
        self,
        token: str,
        telegram_user_id: int,
        telegram_username: str | None = None,
        language_code: str = "id",
        currency: str = "IDR",
        timezone: str = "Asia/Jakarta",
    ) -> dict[str, Any]:
        """Atomically claim a registration token via the Postgres RPC.

        Returns a dict with ``ok`` (bool) and either ``user_id`` (str) on
        success or ``error`` (str) on failure.  The error key is one of
        ``CLAIM_ERROR_*`` constants.
        """
        result = self.client.rpc(
            "claim_registration_token",
            {
                "p_token": token,
                "p_telegram_user_id": telegram_user_id,
                "p_telegram_username": telegram_username,
                "p_language_code": language_code,
                "p_currency": currency,
                "p_timezone": timezone,
            },
        ).execute()
        data = result.data
        if isinstance(data, dict):
            return data
        if isinstance(data, list) and data:
            row = data[0]
            if isinstance(row, dict):
                return row
        return {CLAIM_OK: False, "error": "not_found"}

    def mark_expired(self, limit: int = 200) -> int:
        """Flip unclaimed past-expiry tokens to ``expired`` status via RPC."""
        result = self.client.rpc(
            "mark_expired_registration_tokens",
            {"p_limit": limit},
        ).execute()
        rows = self.rows(result)
        if rows and isinstance(rows[0], (int, float)):
            return int(rows[0])
        return 0