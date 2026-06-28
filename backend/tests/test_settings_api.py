from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_users_repository
from app.main import app
from app.repositories.users_repository import UsersRepository
from tests.test_repositories import FakeSupabaseClient

CURRENT_USER = {
    "id": "user-1",
    "telegram_user_id": 111,
    "role": "user",
    "status": "active",
    "onboarding_status": "completed",
    "cashflow_period_start_day": 1,
}


def settings_client(repository: UsersRepository) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: CURRENT_USER
    app.dependency_overrides[get_users_repository] = lambda: repository
    return TestClient(app)


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_read_settings_returns_cashflow_period_start_day() -> None:
    repository = UsersRepository(FakeSupabaseClient())
    client = settings_client(repository)

    try:
        response = client.get("/settings")
    finally:
        clear_overrides()

    assert response.status_code == 200
    assert response.json() == {"cashflow_period_start_day": 1}


def test_update_cashflow_period_start_day() -> None:
    repository = UsersRepository(FakeSupabaseClient())
    repository.table().insert({**CURRENT_USER}).execute()
    client = settings_client(repository)

    try:
        response = client.patch(
            "/settings/cashflow-period",
            json={"cashflow_period_start_day": 29},
        )
        invalid = client.patch(
            "/settings/cashflow-period",
            json={"cashflow_period_start_day": 32},
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    assert response.json() == {"cashflow_period_start_day": 29}
    assert invalid.status_code == 422
    updated = repository.get_by_id("user-1")
    assert updated is not None
    assert updated["cashflow_period_start_day"] == 29
