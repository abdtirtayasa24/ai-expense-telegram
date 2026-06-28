from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_current_user,
    get_settings,
    get_transactions_repository,
    get_users_repository,
)
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


def transaction_client(repository: TransactionsRepository) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: CURRENT_USER
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


def test_transactions_require_jwt_auth() -> None:
    repository = TransactionsRepository(FakeSupabaseClient())
    app.dependency_overrides[get_settings] = lambda: object()
    app.dependency_overrides[get_users_repository] = lambda: object()
    app.dependency_overrides[get_transactions_repository] = lambda: repository
    client = TestClient(app)

    try:
        response = client.get("/transactions")
    finally:
        clear_overrides()

    assert response.status_code == 401


def test_list_transactions_returns_current_user_data_with_filters() -> None:
    repository = TransactionsRepository(FakeSupabaseClient())
    own_june = seed_transaction(repository, name="Parkir")
    seed_transaction(
        repository,
        name="Kopi",
        category="makanan_minuman",
        amount=Decimal("18000"),
    )
    seed_transaction(
        repository,
        name="Gaji",
        category="pendapatan",
        transaction_type="income",
        amount=Decimal("8000000"),
    )
    seed_transaction(repository, user_id="user-2", name="Rahasia")
    seed_transaction(repository, name="Juli", transaction_date=date(2026, 7, 1))
    client = transaction_client(repository)

    try:
        response = client.get(
            "/transactions?month=2026-06&type=expense&category=transportasi&limit=10&offset=0"
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": own_june["id"],
                "type": "expense",
                "name": "Parkir",
                "category": "transportasi",
                "amount": 5000.0,
                "transaction_date": "2026-06-26",
                "note": None,
                "source": "manual",
                "parser": "manual",
                "confidence_score": None,
            }
        ],
        "limit": 10,
        "offset": 0,
        "has_next": False,
    }


def test_list_transactions_returns_has_next_when_more_rows_exist() -> None:
    repository = TransactionsRepository(FakeSupabaseClient())
    for index in range(11):
        seed_transaction(repository, name=f"Transaksi {index}")
    client = transaction_client(repository)

    try:
        response = client.get("/transactions?limit=10&offset=0")
    finally:
        clear_overrides()

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 10
    assert body["limit"] == 10
    assert body["offset"] == 0
    assert body["has_next"] is True


def test_create_transaction_sets_manual_source_and_parser() -> None:
    repository = TransactionsRepository(FakeSupabaseClient())
    client = transaction_client(repository)

    try:
        response = client.post(
            "/transactions",
            json={
                "type": "expense",
                "name": "Parkir kantor",
                "category": "transportasi",
                "amount": 7000,
                "transaction_date": "2026-06-26",
                "note": "Parkir kantor",
            },
        )
    finally:
        clear_overrides()

    assert response.status_code == 201
    body = response.json()
    assert body["source"] == "manual"
    assert body["parser"] == "manual"
    assert body["name"] == "Parkir kantor"
    assert repository.list_for_user("user-1")[0]["user_id"] == "user-1"


def test_update_and_delete_scope_to_current_user() -> None:
    repository = TransactionsRepository(FakeSupabaseClient())
    own = seed_transaction(repository)
    other = seed_transaction(repository, user_id="user-2", name="Milik orang")
    client = transaction_client(repository)

    try:
        update_own = client.patch(
            f"/transactions/{own['id']}",
            json={"amount": 9000, "name": "Parkir gedung"},
        )
        update_other = client.patch(
            f"/transactions/{other['id']}",
            json={"name": "Tidak boleh"},
        )
        delete_other = client.delete(f"/transactions/{other['id']}")
        delete_own = client.delete(f"/transactions/{own['id']}")
    finally:
        clear_overrides()

    assert update_own.status_code == 200
    assert update_own.json()["amount"] == 9000.0
    assert update_own.json()["name"] == "Parkir gedung"
    assert update_other.status_code == 404
    assert delete_other.status_code == 404
    assert repository.get_for_user(other["id"], "user-2") is not None
    assert delete_own.status_code == 200
    assert delete_own.json() == {"deleted": True}
    assert repository.get_for_user(own["id"], "user-1") is None


def test_update_can_clear_note() -> None:
    repository = TransactionsRepository(FakeSupabaseClient())
    transaction = repository.create(
        user_id="user-1",
        transaction_type="expense",
        name="Parkir",
        category="transportasi",
        amount=Decimal("5000"),
        transaction_date=date(2026, 6, 26),
        source="manual",
        parser="manual",
        note="Catatan lama",
    )
    client = transaction_client(repository)

    try:
        response = client.patch(
            f"/transactions/{transaction['id']}",
            json={"note": None},
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    assert response.json()["note"] is None
    stored = repository.get_for_user(transaction["id"], "user-1")
    assert stored is not None
    assert stored["note"] is None


def test_transaction_validation_errors() -> None:
    repository = TransactionsRepository(FakeSupabaseClient())
    client = transaction_client(repository)

    try:
        invalid_month = client.get("/transactions?month=2026-13")
        invalid_limit = client.get("/transactions?limit=101")
        invalid_create = client.post(
            "/transactions",
            json={
                "type": "expense",
                "name": "",
                "category": "not-a-category",
                "amount": 0,
                "transaction_date": "not-a-date",
            },
        )
    finally:
        clear_overrides()

    assert invalid_month.status_code == 422
    assert invalid_limit.status_code == 422
    assert invalid_create.status_code == 422
