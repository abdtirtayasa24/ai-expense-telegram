from datetime import date
from typing import Any

from app.repositories.base import BaseRepository, Row


class InsightsRepository(BaseRepository):
    table_name = "advisor_insights"

    def create(
        self,
        user_id: str,
        period_start: date,
        period_end: date,
        insight_type: str,
        summary: str,
        generated_by: str = "gemini",
        result: dict[str, Any] | None = None,
        context_hash: str | None = None,
    ) -> Row:
        payload = {
            "user_id": user_id,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "insight_type": insight_type,
            "summary": summary,
            "generated_by": generated_by,
            "result": result,
            "context_hash": context_hash,
        }
        result = self.table().insert(payload).execute()
        row = self.first(result)
        if row is None:
            raise RuntimeError("Supabase did not return the created advisor insight.")
        return row

    def list_for_user_period(
        self,
        user_id: str,
        period_start: date,
        period_end: date,
    ) -> list[Row]:
        result = (
            self.table()
            .select("*")
            .eq("user_id", user_id)
            .eq("period_start", period_start.isoformat())
            .eq("period_end", period_end.isoformat())
            .order("created_at", desc=True)
            .execute()
        )
        return self.rows(result)

    def get_cached_for_context(
        self,
        user_id: str,
        period_start: date,
        period_end: date,
        insight_type: str,
        context_hash: str,
    ) -> Row | None:
        result = (
            self.table()
            .select("*")
            .eq("user_id", user_id)
            .eq("period_start", period_start.isoformat())
            .eq("period_end", period_end.isoformat())
            .eq("insight_type", insight_type)
            .eq("context_hash", context_hash)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return self.first(result)

    def get_for_user(self, insight_id: str, user_id: str) -> Row | None:
        result = (
            self.table()
            .select("*")
            .eq("id", insight_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return self.first(result)
