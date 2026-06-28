from typing import Any, Literal

from app.repositories.base import BaseRepository, Row

AdvisorChatRole = Literal["user", "assistant"]
AdvisorChatSource = Literal["telegram_chat", "mini_app"]


class AdvisorChatRepository(BaseRepository):
    table_name = "advisor_chat_messages"

    def create_message(
        self,
        user_id: str,
        role: AdvisorChatRole,
        content: str,
        source: AdvisorChatSource,
        metadata: dict[str, Any] | None = None,
    ) -> Row:
        payload = {
            "user_id": user_id,
            "role": role,
            "content": content,
            "source": source,
            "metadata": metadata or {},
        }
        result = self.table().insert(payload).execute()
        row = self.first(result)
        if row is None:
            raise RuntimeError(
                "Supabase did not return the created advisor chat message."
            )
        return row

    def list_recent_for_user(self, user_id: str, limit: int) -> list[Row]:
        result = (
            self.table()
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(reversed(self.rows(result)))
