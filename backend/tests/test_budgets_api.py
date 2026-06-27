from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_budgets_repository,
    get_current_user,
    get_transactions_repository,
)
from app.main import app
from app.repositories.budgets_repository import BudgetsRepository
from app.repositories.transactions_repository import TransactionsRepository
from tests.test_repositories import FakeSupabaseClient

CURRENT_USER = {
    "id": "user-1",
    "telegram_user_id": 111,
    "role": "user",
    "status": "active",
    "onboarding_status": "completed",
}


def budget_client(
    budgets_repository: BudgetsRepository,
    transactions_repository: TransactionsRepository,
) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: CURRENT_USER
    app.dependency_overrides[get_budgets_repository] = lambda: budgets_repository
    app.dependency_overrides[get_transactions_repository] = (
        lambda: transactions_repository
    )
    return TestClient(app)


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def seed_transaction(
    repository: TransactionsRepository,
    user_id: str = "user-1",
    transaction_type: str = "expense",
    name: str = "Parkir",
    category: str = "transportasi",
    amount: Decimal = Decimal("5000"),
    transaction_date: date = date(2026, 6, 26),
) -> dict:
    return repository.create(
        user_id=user_id,
        transaction_type=transaction_type,  # type: ignore[arg-type]
        name=name,
        category=category,
        amount=amount,
        transaction_date=transaction_date,
        source="manual",
        parser="manual",
    )


def test_budget_creation_and_list_with_actuals() -> None:
    budgets = BudgetsRepository(FakeSupabaseClient())
    transactions = TransactionsRepository(FakeSupabaseClient())
    seed_transaction(transactions, category="transportasi", amount=Decimal("75000"))
    seed_transaction(transactions, category="makanan_minuman", amount=Decimal("50000"))
    seed_transaction(
        transactions,
        transaction_type="income",
        category="pendapatan",
        amount=Decimal("100000"),
    )
    seed_transaction(transactions, user_id="user-2", amount=Decimal("999999"))
    client = budget_client(budgets, transactions)

    try:
        created = client.post(
            "/budgets",
            json={
                "category": "transportasi",
                "monthly_limit": 100000,
                "month": "2026-06-01",
            },
        )
        listed = client.get("/budgets?month=2026-06")
    finally:
        clear_overrides()

    assert created.status_code == 201
    assert created.json()["actual"] == 75000.0
    assert created.json()["remaining"] == 25000.0
    assert created.json()["percent_used"] == 75.0
    assert listed.json()["items"][0]["actual"] == 75000.0


def test_budget_duplicate_rejects_with_conflict() -> None:
    budgets = BudgetsRepository(FakeSupabaseClient())
    transactions = TransactionsRepository(FakeSupabaseClient())
    client = budget_client(budgets, transactions)

    try:
        first = client.post(
            "/budgets",
            json={
                "category": "transportasi",
                "monthly_limit": 100000,
                "month": "2026-06-01",
            },
        )
        duplicate = client.post(
            "/budgets",
            json={
                "category": "transportasi",
                "monthly_limit": 50000,
                "month": "2026-06-01",
            },
        )
    finally:
        clear_overrides()

    assert first.status_code == 201
    assert duplicate.status_code == 409


def test_budget_update_and_delete_scope_to_current_user() -> None:
    budgets = BudgetsRepository(FakeSupabaseClient())
    transactions = TransactionsRepository(FakeSupabaseClient())
    own = budgets.create("user-1", "transportasi", Decimal("100000"), date(2026, 6, 1))
    other = budgets.create(
        "user-2",
        "makanan_minuman",
        Decimal("50000"),
        date(2026, 6, 1),
    )
    client = budget_client(budgets, transactions)

    try:
        update_own = client.patch(
            f"/budgets/{own['id']}",
            json={"monthly_limit": 150000},
        )
        update_other = client.patch(
            f"/budgets/{other['id']}",
            json={"monthly_limit": 999},
        )
        delete_other = client.delete(f"/budgets/{other['id']}")
        delete_own = client.delete(f"/budgets/{own['id']}")
    finally:
        clear_overrides()

    assert update_own.status_code == 200
    assert update_own.json()["monthly_limit"] == 150000.0
    assert update_other.status_code == 404
    assert delete_other.status_code == 404
    assert delete_own.status_code == 200
    assert delete_own.json() == {"deleted": True}
    assert budgets.get_for_user(own["id"], "user-1") is None


def test_budget_validation_errors() -> None:
    budgets = BudgetsRepository(FakeSupabaseClient())
    transactions = TransactionsRepository(FakeSupabaseClient())
    client = budget_client(budgets, transactions)

    try:
        invalid_month = client.get("/budgets?month=2026-13")
        invalid_category = client.post(
            "/budgets",
            json={
                "category": "not-a-category",
                "monthly_limit": 100000,
                "month": "2026-06-01",
            },
        )
        invalid_limit = client.post(
            "/budgets",
            json={
                "category": "transportasi",
                "monthly_limit": 0,
                "month": "2026-06-01",
            },
        )
    finally:
        clear_overrides()

    assert invalid_month.status_code == 422
    assert invalid_category.status_code == 422
    assert invalid_limit.status_code == 422


def test_budget_over_budget_category_detected() -> None:
    budgets = BudgetsRepository(FakeSupabaseClient())
    transactions = TransactionsRepository(FakeSupabaseClient())
    seed_transaction(transactions, category="transportasi", amount=Decimal("150000"))
    client = budget_client(budgets, transactions)

    try:
        created = client.post(
            "/budgets",
            json={
                "category": "transportasi",
                "monthly_limit": 100000,
                "month": "2026-06-01",
            },
        )
    finally:
        clear_overrides()

    assert created.status_code == 201
    assert created.json()["actual"] == 150000.0
    assert created.json()["remaining"] == -50000.0
    assert created.json()["percent_used"] == 150.0
