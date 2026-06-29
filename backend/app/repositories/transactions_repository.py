from datetime import date
from decimal import Decimal
from typing import Any, Literal

from app.repositories.base import BaseRepository, QueryBuilder, Row

TransactionType = Literal["income", "expense"]
ParserType = Literal["rule_based", "gemini", "manual"]
SourceType = Literal["telegram_chat", "manual"]


class TransactionsRepository(BaseRepository):
    table_name = "transactions"

    def create(
        self,
        user_id: str,
        transaction_type: TransactionType,
        name: str,
        category: str,
        amount: Decimal,
        transaction_date: date,
        source: SourceType,
        parser: ParserType,
        note: str | None = None,
        confidence_score: float | None = None,
        raw_message: str | None = None,
    ) -> Row:
        payload: dict[str, Any] = {
            "user_id": user_id,
            "type": transaction_type,
            "name": name,
            "category": category,
            "amount": str(amount),
            "transaction_date": transaction_date.isoformat(),
            "note": note,
            "source": source,
            "parser": parser,
            "confidence_score": confidence_score,
            "raw_message": raw_message,
        }
        result = self.table().insert(payload).execute()
        row = self.first(result)
        if row is None:
            raise RuntimeError("Supabase did not return the created transaction.")
        return row

    def list_for_user(
        self,
        user_id: str,
        month_start: date | None = None,
        next_month_start: date | None = None,
        transaction_type: TransactionType | None = None,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Row]:
        query = self.table().select("*").eq("user_id", user_id)
        query = self._apply_filters(
            query,
            month_start=month_start,
            next_month_start=next_month_start,
            transaction_type=transaction_type,
            category=category,
        )
        end = offset + limit - 1
        result = (
            query.order("transaction_date", desc=True)
            .order("created_at", desc=True)
            .range(offset, end)
            .execute()
        )
        return self.rows(result)

    def get_for_user(self, transaction_id: str, user_id: str) -> Row | None:
        result = (
            self.table()
            .select("*")
            .eq("id", transaction_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return self.first(result)

    def update_for_user(
        self,
        transaction_id: str,
        user_id: str,
        updates: dict[str, Any],
    ) -> Row | None:
        payload = {
            key: value
            for key, value in updates.items()
            if value is not None or key == "note"
        }
        if "amount" in payload and isinstance(payload["amount"], Decimal):
            payload["amount"] = str(payload["amount"])
        if "transaction_date" in payload and isinstance(
            payload["transaction_date"], date
        ):
            payload["transaction_date"] = payload["transaction_date"].isoformat()
        if not payload:
            return self.get_for_user(transaction_id, user_id)
        result = (
            self.table()
            .update(payload)
            .eq("id", transaction_id)
            .eq("user_id", user_id)
            .execute()
        )
        return self.first(result)

    def delete_for_user(self, transaction_id: str, user_id: str) -> bool:
        result = (
            self.table()
            .delete()
            .eq("id", transaction_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(result.data)

    @staticmethod
    def _apply_filters(
        query: QueryBuilder,
        month_start: date | None,
        next_month_start: date | None,
        transaction_type: TransactionType | None,
        category: str | None,
    ) -> QueryBuilder:
        if month_start is not None:
            query = query.gte("transaction_date", month_start.isoformat())
        if next_month_start is not None:
            query = query.lt("transaction_date", next_month_start.isoformat())
        if transaction_type is not None:
            query = query.eq("type", transaction_type)
        if category is not None:
            query = query.eq("category", category)
        return query
