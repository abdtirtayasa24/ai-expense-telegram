from datetime import date
from decimal import Decimal
from typing import Any

from app.repositories.base import BaseRepository, Row


class BudgetsRepository(BaseRepository):
    table_name = "budgets"

    def create(
        self,
        user_id: str,
        category: str,
        monthly_limit: Decimal,
        month: date,
    ) -> Row:
        payload = {
            "user_id": user_id,
            "category": category,
            "monthly_limit": str(monthly_limit),
            "month": month.isoformat(),
        }
        result = self.table().insert(payload).execute()
        row = self.first(result)
        if row is None:
            raise RuntimeError("Supabase did not return the created budget.")
        return row

    def list_for_user_month(self, user_id: str, month: date) -> list[Row]:
        result = (
            self.table()
            .select("*")
            .eq("user_id", user_id)
            .eq("month", month.isoformat())
            .order("category")
            .execute()
        )
        return self.rows(result)

    def get_for_user(self, budget_id: str, user_id: str) -> Row | None:
        result = (
            self.table()
            .select("*")
            .eq("id", budget_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return self.first(result)

    def update_for_user(
        self,
        budget_id: str,
        user_id: str,
        updates: dict[str, Any],
    ) -> Row | None:
        payload = {key: value for key, value in updates.items() if value is not None}
        if "monthly_limit" in payload and isinstance(payload["monthly_limit"], Decimal):
            payload["monthly_limit"] = str(payload["monthly_limit"])
        if "month" in payload and isinstance(payload["month"], date):
            payload["month"] = payload["month"].isoformat()
        if not payload:
            return self.get_for_user(budget_id, user_id)
        result = (
            self.table()
            .update(payload)
            .eq("id", budget_id)
            .eq("user_id", user_id)
            .execute()
        )
        return self.first(result)

    def delete_for_user(self, budget_id: str, user_id: str) -> bool:
        result = (
            self.table()
            .delete()
            .eq("id", budget_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(result.data)
