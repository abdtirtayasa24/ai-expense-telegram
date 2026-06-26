from datetime import UTC, datetime
from typing import Any

from app.core.defaults import DEFAULT_CURRENCY, DEFAULT_LANGUAGE, DEFAULT_TIMEZONE
from app.repositories.base import BaseRepository, Row


class UsersRepository(BaseRepository):
    table_name = "users"

    def get_by_id(self, user_id: str) -> Row | None:
        result = self.table().select("*").eq("id", user_id).limit(1).execute()
        return self.first(result)

    def get_by_telegram_user_id(self, telegram_user_id: int) -> Row | None:
        result = (
            self.table()
            .select("*")
            .eq("telegram_user_id", telegram_user_id)
            .limit(1)
            .execute()
        )
        return self.first(result)

    def create_registered_user(
        self,
        telegram_user_id: int,
        registered_by_telegram_id: int,
        telegram_username: str | None = None,
        role: str = "user",
    ) -> Row:
        now = datetime.now(UTC).isoformat()
        payload: dict[str, Any] = {
            "telegram_user_id": telegram_user_id,
            "telegram_username": telegram_username,
            "role": role,
            "status": "active",
            "onboarding_status": "pending",
            "language_code": DEFAULT_LANGUAGE,
            "currency": DEFAULT_CURRENCY,
            "timezone": DEFAULT_TIMEZONE,
            "registered_by_telegram_id": registered_by_telegram_id,
            "registered_at": now,
            "unregistered_at": None,
        }
        result = self.table().insert(payload).execute()
        row = self.first(result)
        if row is None:
            raise RuntimeError("Supabase did not return the created user.")
        return row

    def update_profile(
        self,
        user_id: str,
        first_name: str | None = None,
        last_name: str | None = None,
        telegram_username: str | None = None,
    ) -> Row | None:
        payload = self._without_none(
            {
                "first_name": first_name,
                "last_name": last_name,
                "telegram_username": telegram_username,
            }
        )
        if not payload:
            return self.get_by_id(user_id)
        result = self.table().update(payload).eq("id", user_id).execute()
        return self.first(result)

    def update_onboarding_status(
        self,
        user_id: str,
        onboarding_status: str,
    ) -> Row | None:
        result = (
            self.table()
            .update({"onboarding_status": onboarding_status})
            .eq("id", user_id)
            .execute()
        )
        return self.first(result)

    def deactivate(self, telegram_user_id: int) -> Row | None:
        result = (
            self.table()
            .update(
                {
                    "status": "inactive",
                    "unregistered_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("telegram_user_id", telegram_user_id)
            .execute()
        )
        return self.first(result)

    def reactivate(
        self,
        telegram_user_id: int,
        registered_by_telegram_id: int,
        reset_onboarding: bool = False,
    ) -> Row | None:
        payload: dict[str, Any] = {
            "status": "active",
            "registered_by_telegram_id": registered_by_telegram_id,
            "registered_at": datetime.now(UTC).isoformat(),
            "unregistered_at": None,
        }
        if reset_onboarding:
            payload["onboarding_status"] = "pending"
        result = (
            self.table()
            .update(payload)
            .eq("telegram_user_id", telegram_user_id)
            .execute()
        )
        return self.first(result)

    def list_users(self) -> list[Row]:
        result = self.table().select("*").order("created_at").execute()
        return self.rows(result)

    @staticmethod
    def _without_none(payload: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in payload.items() if value is not None}
