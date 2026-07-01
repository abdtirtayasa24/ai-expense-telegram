from datetime import UTC, datetime

from app.repositories.base import BaseRepository, Row


class PendingTokenClaimsRepository(BaseRepository):
    table_name = "pending_token_claims"

    def upsert(
        self,
        telegram_user_id: int,
        chat_id: int,
        expires_at: datetime,
    ) -> Row:
        """Insert or refresh a pending token claim for an unregistered user."""
        existing = self.get_for_telegram_user_id(telegram_user_id)
        if existing is not None:
            result = (
                self.table()
                .update(
                    {
                        "chat_id": chat_id,
                        "expires_at": expires_at.isoformat(),
                    }
                )
                .eq("telegram_user_id", telegram_user_id)
                .execute()
            )
            row = self.first(result)
            if row is not None:
                return row
        payload = {
            "telegram_user_id": telegram_user_id,
            "chat_id": chat_id,
            "expires_at": expires_at.isoformat(),
        }
        result = self.table().insert(payload).execute()
        row = self.first(result)
        if row is None:
            raise RuntimeError(
                "Supabase did not return the created pending token claim."
            )
        return row

    def get_active(self, telegram_user_id: int) -> Row | None:
        result = (
            self.table()
            .select("*")
            .eq("telegram_user_id", telegram_user_id)
            .gte("expires_at", datetime.now(UTC).isoformat())
            .limit(1)
            .execute()
        )
        return self.first(result)

    def get_for_telegram_user_id(self, telegram_user_id: int) -> Row | None:
        result = (
            self.table()
            .select("*")
            .eq("telegram_user_id", telegram_user_id)
            .limit(1)
            .execute()
        )
        return self.first(result)

    def delete(self, telegram_user_id: int) -> bool:
        result = (
            self.table()
            .delete()
            .eq("telegram_user_id", telegram_user_id)
            .execute()
        )
        return bool(result.data)

    def delete_expired(self, limit: int = 200) -> int:
        """Delete expired pending claims via the Postgres RPC."""
        result = self.client.rpc(
            "delete_expired_pending_token_claims",
            {"p_limit": limit},
        ).execute()
        rows = self.rows(result)
        if rows and isinstance(rows[0], (int, float)):
            return int(rows[0])
        return 0