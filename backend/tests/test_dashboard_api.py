from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_transactions_repository
from app.main import app
from app.repositories.transactions_repository import TransactionsRepository
from tests.test_repositories import FakeSupabaseClient

CURRENT_USER = {
    "id": "user-1",
    "telegram_user_id": 111,
    "role": "user",
    "status": "active",
    "onboarding_status": "completed",
}


def dashboard_client(
    repository: TransactionsRepository,
    current_user: dict | None = None,
) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: current_user or CURRENT_USER
    app.dependency_overrides[get_transactions_repository] = lambda: repository
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


def add_months(value: date, delta: int) -> date:
    month_index = value.year * 12 + (value.month - 1) + delta
    return date(month_index // 12, (month_index % 12) + 1, 1)


def test_dashboard_summary_calculates_current_user_month_totals() -> None:
    repository = TransactionsRepository(FakeSupabaseClient())
    seed_transaction(repository, amount=Decimal("25000"), category="transportasi")
    seed_transaction(
        repository,
        transaction_type="income",
        name="Gaji",
        category="pendapatan",
        amount=Decimal("100000"),
    )
    seed_transaction(repository, user_id="user-2", amount=Decimal("999999"))
    seed_transaction(
        repository,
        amount=Decimal("10000"),
        transaction_date=date(2026, 7, 1),
    )
    client = dashboard_client(repository)

    try:
        response = client.get("/dashboard/summary?month=2026-06")
    finally:
        clear_overrides()

    assert response.status_code == 200
    assert response.json() == {
        "month": "2026-06",
        "income_total": 100000.0,
        "expense_total": 25000.0,
        "net_cashflow": 75000.0,
        "savings_rate_percent": 75.0,
    }


def test_dashboard_summary_uses_custom_cashflow_period() -> None:
    repository = TransactionsRepository(FakeSupabaseClient())
    current_user = {**CURRENT_USER, "cashflow_period_start_day": 29}
    seed_transaction(
        repository,
        transaction_type="income",
        name="Gaji",
        category="pendapatan",
        amount=Decimal("100000"),
        transaction_date=date(2026, 6, 29),
    )
    seed_transaction(
        repository,
        amount=Decimal("25000"),
        transaction_date=date(2026, 7, 1),
    )
    seed_transaction(
        repository,
        amount=Decimal("999999"),
        transaction_date=date(2026, 6, 28),
    )
    client = dashboard_client(repository, current_user)

    try:
        response = client.get("/dashboard/summary?month=2026-06")
    finally:
        clear_overrides()

    assert response.status_code == 200
    assert response.json() == {
        "month": "2026-06-29",
        "income_total": 100000.0,
        "expense_total": 25000.0,
        "net_cashflow": 75000.0,
        "savings_rate_percent": 75.0,
    }


def test_dashboard_summary_includes_more_than_one_repository_page() -> None:
    repository = TransactionsRepository(FakeSupabaseClient())
    for index in range(1001):
        seed_transaction(
            repository,
            name=f"Transaksi {index}",
            amount=Decimal("1"),
        )
    client = dashboard_client(repository)

    try:
        response = client.get("/dashboard/summary?month=2026-06")
    finally:
        clear_overrides()

    assert response.status_code == 200
    assert response.json()["expense_total"] == 1001.0
    assert response.json()["net_cashflow"] == -1001.0


def test_dashboard_categories_returns_expense_breakdown_percentages() -> None:
    repository = TransactionsRepository(FakeSupabaseClient())
    seed_transaction(repository, amount=Decimal("25000"), category="transportasi")
    seed_transaction(
        repository,
        name="Kopi",
        category="makanan_minuman",
        amount=Decimal("75000"),
    )
    seed_transaction(
        repository,
        transaction_type="income",
        category="pendapatan",
        amount=Decimal("100000"),
    )
    seed_transaction(repository, user_id="user-2", amount=Decimal("999999"))
    client = dashboard_client(repository)

    try:
        response = client.get("/dashboard/categories?month=2026-06")
    finally:
        clear_overrides()

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"category": "makanan_minuman", "amount": 75000.0, "percent": 75.0},
            {"category": "transportasi", "amount": 25000.0, "percent": 25.0},
        ]
    }


def test_dashboard_trend_returns_monthly_totals_for_current_user_only() -> None:
    repository = TransactionsRepository(FakeSupabaseClient())
    current = datetime.now(ZoneInfo("Asia/Jakarta")).date().replace(day=1)
    previous = add_months(current, -1)
    seed_transaction(
        repository,
        transaction_type="income",
        amount=Decimal("100000"),
        transaction_date=current,
    )
    seed_transaction(repository, amount=Decimal("40000"), transaction_date=current)
    seed_transaction(repository, amount=Decimal("25000"), transaction_date=previous)
    seed_transaction(
        repository,
        user_id="user-2",
        amount=Decimal("999999"),
        transaction_date=current,
    )
    client = dashboard_client(repository)

    try:
        response = client.get("/dashboard/trend?months=2")
    finally:
        clear_overrides()

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "month": previous.strftime("%Y-%m"),
                "income_total": 0.0,
                "expense_total": 25000.0,
                "net_cashflow": -25000.0,
            },
            {
                "month": current.strftime("%Y-%m"),
                "income_total": 100000.0,
                "expense_total": 40000.0,
                "net_cashflow": 60000.0,
            },
        ]
    }


def test_dashboard_recent_transactions_are_scoped_and_limited() -> None:
    repository = TransactionsRepository(FakeSupabaseClient())
    older = seed_transaction(
        repository,
        name="Lama",
        transaction_date=date(2026, 6, 1),
    )
    newer = seed_transaction(
        repository,
        name="Baru",
        transaction_date=date(2026, 6, 30),
    )
    seed_transaction(
        repository,
        user_id="user-2",
        name="Rahasia",
        transaction_date=date(2026, 7, 1),
    )
    client = dashboard_client(repository)

    try:
        response = client.get("/dashboard/recent-transactions?limit=2")
    finally:
        clear_overrides()

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["id"] for item in items] == [newer["id"], older["id"]]


def test_dashboard_empty_data_and_validation_errors() -> None:
    repository = TransactionsRepository(FakeSupabaseClient())
    client = dashboard_client(repository)

    try:
        empty_summary = client.get("/dashboard/summary?month=2026-06")
        empty_categories = client.get("/dashboard/categories?month=2026-06")
        invalid_month = client.get("/dashboard/summary?month=2026-13")
        invalid_months = client.get("/dashboard/trend?months=25")
        invalid_limit = client.get("/dashboard/recent-transactions?limit=51")
    finally:
        clear_overrides()

    assert empty_summary.status_code == 200
    assert empty_summary.json()["income_total"] == 0.0
    assert empty_summary.json()["expense_total"] == 0.0
    assert empty_categories.status_code == 200
    assert empty_categories.json() == {"items": []}
    assert invalid_month.status_code == 422
    assert invalid_months.status_code == 422
    assert invalid_limit.status_code == 422
