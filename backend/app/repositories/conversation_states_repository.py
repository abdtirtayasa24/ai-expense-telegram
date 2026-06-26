from datetime import UTC, datetime
from typing import Any

from app.repositories.base import BaseRepository, Row


class ConversationStatesRepository(BaseRepository):
    table_name = "conversation_states"

    def create(
        self,
        user_id: str,
        state: str,
        expires_at: datetime,
        payload: dict[str, Any] | None = None,
    ) -> Row:
        row_payload = {
            "user_id": user_id,
            "state": state,
            "payload": payload or {},
            "expires_at": expires_at.isoformat(),
        }
        result = self.table().insert(row_payload).execute()
        row = self.first(result)
        if row is None:
            raise RuntimeError(
                "Supabase did not return the created conversation state."
            )
        return row

    def get_active_for_user(self, user_id: str, state: str | None = None) -> Row | None:
        query = (
            self.table()
            .select("*")
            .eq("user_id", user_id)
            .gte("expires_at", datetime.now(UTC).isoformat())
        )
        if state is not None:
            query = query.eq("state", state)
        result = query.order("created_at", desc=True).limit(1).execute()
        return self.first(result)

    def update_for_user(
        self,
        state_id: str,
        user_id: str,
        updates: dict[str, Any],
    ) -> Row | None:
        payload = {key: value for key, value in updates.items() if value is not None}
        if "expires_at" in payload and isinstance(payload["expires_at"], datetime):
            payload["expires_at"] = payload["expires_at"].isoformat()
        if not payload:
            result = (
                self.table()
                .select("*")
                .eq("id", state_id)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            return self.first(result)
        result = (
            self.table()
            .update(payload)
            .eq("id", state_id)
            .eq("user_id", user_id)
            .execute()
        )
        return self.first(result)

    def delete_for_user(self, state_id: str, user_id: str) -> bool:
        result = (
            self.table()
            .delete()
            .eq("id", state_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(result.data)

    def delete_expired_for_user(self, user_id: str) -> int:
        result = (
            self.table()
            .delete()
            .eq("user_id", user_id)
            .lt("expires_at", datetime.now(UTC).isoformat())
            .execute()
        )
        return len(result.data or [])
