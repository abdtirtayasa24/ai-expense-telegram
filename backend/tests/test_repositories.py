from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from app.repositories.budgets_repository import BudgetsRepository
from app.repositories.conversation_states_repository import ConversationStatesRepository
from app.repositories.insights_repository import InsightsRepository
from app.repositories.transactions_repository import TransactionsRepository
from app.repositories.users_repository import UsersRepository


@dataclass
class FakeResult:
    data: list[dict[str, Any]] | None


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {}
        self.next_id = 1

    def table(self, table_name: str) -> FakeQueryBuilder:
        self.tables.setdefault(table_name, [])
        return FakeQueryBuilder(self, table_name)

    def rpc(self, function_name: str, params: dict[str, Any]) -> FakeRpcBuilder:
        return FakeRpcBuilder(self, function_name, params)

    def make_id(self) -> str:
        value = f"id-{self.next_id}"
        self.next_id += 1
        return value


class FakeRpcBuilder:
    def __init__(
        self,
        client: FakeSupabaseClient,
        function_name: str,
        params: dict[str, Any],
    ) -> None:
        self.client = client
        self.function_name = function_name
        self.params = params

    def execute(self) -> FakeResult:
        if self.function_name != "claim_expired_conversation_states":
            raise AssertionError(f"Unsupported RPC: {self.function_name}")

        state = self.params["p_state"]
        limit = self.params.get("p_limit", 100)
        now = datetime.now(UTC).isoformat()
        rows = [
            row
            for row in self.client.tables.get("conversation_states", [])
            if row.get("state") == state and row.get("expires_at") < now
        ]
        rows.sort(key=lambda row: row.get("expires_at"))
        claimed = rows[:limit]
        for row in claimed:
            payload = dict(row.get("payload") or {})
            payload["timeout_claimed_at"] = now
            row["payload"] = payload
        return FakeResult([deepcopy(row) for row in claimed])


class FakeQueryBuilder:
    def __init__(self, client: FakeSupabaseClient, table_name: str) -> None:
        self.client = client
        self.table_name = table_name
        self.operation = "select"
        self.payload: dict[str, Any] = {}
        self.filters: list[tuple[str, str, Any]] = []
        self.order_by: list[tuple[str, bool]] = []
        self.limit_count: int | None = None
        self.range_bounds: tuple[int, int] | None = None

    def select(self, columns: str = "*") -> FakeQueryBuilder:
        self.operation = "select"
        return self

    def insert(self, json: dict[str, Any]) -> FakeQueryBuilder:
        self.operation = "insert"
        self.payload = dict(json)
        return self

    def update(self, json: dict[str, Any]) -> FakeQueryBuilder:
        self.operation = "update"
        self.payload = dict(json)
        return self

    def delete(self) -> FakeQueryBuilder:
        self.operation = "delete"
        return self

    def eq(self, column: str, value: Any) -> FakeQueryBuilder:
        self.filters.append(("eq", column, value))
        return self

    def gt(self, column: str, value: Any) -> FakeQueryBuilder:
        self.filters.append(("gt", column, value))
        return self

    def gte(self, column: str, value: Any) -> FakeQueryBuilder:
        self.filters.append(("gte", column, value))
        return self

    def lt(self, column: str, value: Any) -> FakeQueryBuilder:
        self.filters.append(("lt", column, value))
        return self

    def order(self, column: str, desc: bool = False) -> FakeQueryBuilder:
        self.order_by.append((column, desc))
        return self

    def limit(self, count: int) -> FakeQueryBuilder:
        self.limit_count = count
        return self

    def range(self, start: int, end: int) -> FakeQueryBuilder:
        self.range_bounds = (start, end)
        return self

    def execute(self) -> FakeResult:
        if self.operation == "insert":
            row = deepcopy(self.payload)
            row.setdefault("id", self.client.make_id())
            row.setdefault("created_at", datetime.now(UTC).isoformat())
            self.client.tables[self.table_name].append(row)
            return FakeResult([deepcopy(row)])

        matched = self._matched_rows()

        if self.operation == "select":
            rows = [deepcopy(row) for row in matched]
            for column, desc in reversed(self.order_by):
                rows.sort(key=lambda row: row.get(column), reverse=desc)
            if self.range_bounds is not None:
                start, end = self.range_bounds
                rows = rows[start : end + 1]
            if self.limit_count is not None:
                rows = rows[: self.limit_count]
            return FakeResult(rows)

        if self.operation == "update":
            for row in matched:
                row.update(self.payload)
            return FakeResult([deepcopy(row) for row in matched])

        if self.operation == "delete":
            deleted = [deepcopy(row) for row in matched]
            self.client.tables[self.table_name] = [
                row for row in self.client.tables[self.table_name] if row not in matched
            ]
            return FakeResult(deleted)

        raise AssertionError(f"Unsupported operation: {self.operation}")

    def _matched_rows(self) -> list[dict[str, Any]]:
        return [
            row
            for row in self.client.tables[self.table_name]
            if all(
                self._matches(row, operator, column, value)
                for operator, column, value in self.filters
            )
        ]

    @staticmethod
    def _matches(
        row: dict[str, Any],
        operator: str,
        column: str,
        value: Any,
    ) -> bool:
        row_value = row.get(column)
        if operator == "eq":
            return row_value == value
        if operator == "gt":
            return row_value > value
        if operator == "gte":
            return row_value >= value
        if operator == "lt":
            return row_value < value
        raise AssertionError(f"Unsupported filter: {operator}")


def test_users_repository_create_update_deactivate_reactivate_and_list() -> None:
    client = FakeSupabaseClient()
    settings = SimpleNamespace(
        default_language="id",
        default_currency="IDR",
        default_timezone="Asia/Jakarta",
    )
    repository = UsersRepository(client, app_settings=settings)

    user = repository.create_registered_user(
        telegram_user_id=123,
        registered_by_telegram_id=999,
        telegram_username="budi",
    )
    assert user["telegram_user_id"] == 123
    assert user["status"] == "active"
    assert user["onboarding_status"] == "pending"

    fetched = repository.get_by_telegram_user_id(123)
    assert fetched is not None
    assert fetched["id"] == user["id"]

    updated = repository.update_profile(
        user["id"],
        first_name="Budi",
        last_name="Santoso",
    )
    assert updated is not None
    assert updated["first_name"] == "Budi"
    assert updated["last_name"] == "Santoso"

    onboarded = repository.update_onboarding_status(user["id"], "completed")
    assert onboarded is not None
    assert onboarded["onboarding_status"] == "completed"

    deactivated = repository.deactivate(123)
    assert deactivated is not None
    assert deactivated["status"] == "inactive"
    assert deactivated["unregistered_at"] is not None

    reactivated = repository.reactivate(123, registered_by_telegram_id=999)
    assert reactivated is not None
    assert reactivated["status"] == "active"
    assert reactivated["unregistered_at"] is None

    assert [row["telegram_user_id"] for row in repository.list_users()] == [123]


def test_transactions_repository_scopes_reads_updates_and_deletes_by_user() -> None:
    client = FakeSupabaseClient()
    repository = TransactionsRepository(client)

    own = repository.create(
        user_id="user-1",
        transaction_type="expense",
        name="Parkir",
        category="transportasi",
        amount=Decimal("5000"),
        transaction_date=date(2026, 6, 26),
        source="telegram_chat",
        parser="rule_based",
        confidence_score=0.92,
        raw_message="Bayar parkir 5000",
    )
    other = repository.create(
        user_id="user-2",
        transaction_type="expense",
        name="Kopi",
        category="makanan_minuman",
        amount=Decimal("18000"),
        transaction_date=date(2026, 6, 26),
        source="telegram_chat",
        parser="rule_based",
    )

    rows = repository.list_for_user("user-1")
    assert [row["id"] for row in rows] == [own["id"]]
    assert repository.get_for_user(other["id"], "user-1") is None

    assert repository.update_for_user(other["id"], "user-1", {"name": "Oops"}) is None
    assert repository.get_for_user(other["id"], "user-2") is not None

    updated = repository.update_for_user(
        own["id"],
        "user-1",
        {"amount": Decimal("7000")},
    )
    assert updated is not None
    assert updated["amount"] == "7000"

    assert repository.delete_for_user(other["id"], "user-1") is False
    assert repository.delete_for_user(own["id"], "user-1") is True
    assert repository.get_for_user(own["id"], "user-1") is None


def test_transactions_repository_lists_by_id_cursor() -> None:
    client = FakeSupabaseClient()
    repository = TransactionsRepository(client)
    for user_id in ("user-1", "user-2", "user-1"):
        repository.create(
            user_id=user_id,
            transaction_type="expense",
            name="Parkir",
            category="transportasi",
            amount=Decimal("5000"),
            transaction_date=date(2026, 6, 26),
            source="telegram_chat",
            parser="rule_based",
        )

    first_page = repository.list_for_user_after_id("user-1", limit=1)
    second_page = repository.list_for_user_after_id(
        "user-1",
        cursor_id=first_page[-1]["id"],
        limit=1,
    )

    assert [row["id"] for row in first_page + second_page] == ["id-1", "id-3"]


def test_budget_insight_and_conversation_state_repositories_scope_by_user() -> None:
    client = FakeSupabaseClient()
    budgets = BudgetsRepository(client)
    insights = InsightsRepository(client)
    states = ConversationStatesRepository(client)

    budget = budgets.create(
        user_id="user-1",
        category="makanan_minuman",
        monthly_limit=Decimal("1500000"),
        month=date(2026, 6, 1),
    )
    assert budgets.get_for_user(budget["id"], "user-2") is None
    assert budgets.get_for_user(budget["id"], "user-1") is not None

    insight = insights.create(
        user_id="user-1",
        period_start=date(2026, 6, 1),
        period_end=date(2026, 7, 1),
        insight_type="monthly_summary",
        summary="Cashflow positif.",
    )
    assert insights.get_for_user(insight["id"], "user-2") is None
    assert insights.get_for_user(insight["id"], "user-1") is not None
    matching_insights = insights.list_for_user_period(
        "user-1",
        period_start=date(2026, 6, 1),
        period_end=date(2026, 7, 1),
    )
    assert [row["id"] for row in matching_insights] == [insight["id"]]
    assert insights.list_for_user_period(
        "user-1",
        period_start=date(2026, 6, 1),
        period_end=date(2026, 8, 1),
    ) == []

    state = states.create(
        user_id="user-1",
        state="awaiting_clarification",
        payload={"raw_message": "parkir"},
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    assert states.update_for_user(state["id"], "user-2", {"state": "wrong"}) is None
    updated_state = states.update_for_user(state["id"], "user-1", {"state": "done"})
    assert updated_state is not None
    assert updated_state["state"] == "done"

    states.create(
        user_id="user-1",
        state="expired",
        expires_at=datetime.now(UTC) - timedelta(minutes=10),
    )
    states.create(
        user_id="user-2",
        state="expired",
        expires_at=datetime.now(UTC) - timedelta(minutes=10),
    )
    assert states.delete_expired_for_user("user-1") == 1
    assert states.get_active_for_user("user-1", "done") is not None
    assert states.delete_expired_for_user("user-2") == 1
