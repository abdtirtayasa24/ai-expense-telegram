"""Advisor guardrail tests — verify prohibited advice is rejected and
supported advice is answered with user-data grounding."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_budgets_repository,
    get_current_user,
    get_insights_repository,
    get_settings,
    get_transactions_repository,
)
from app.main import app
from app.repositories.budgets_repository import BudgetsRepository
from app.repositories.insights_repository import InsightsRepository
from app.repositories.transactions_repository import TransactionsRepository
from app.services.advisor_service import (
    _SYSTEM_INSTRUCTION,
    build_advisor_context,
    generate_chat_answer,
    generate_insights,
)
from tests.test_repositories import FakeSupabaseClient

pytestmark = pytest.mark.asyncio

_CURRENT_USER = {
    "id": "user-1",
    "telegram_user_id": 111,
    "role": "user",
    "status": "active",
    "onboarding_status": "completed",
}

_FAKE_ENV = {
    "APP_BASE_URL": "https://api.example.com",
    "MINI_APP_URL": "https://app.example.com",
    "TELEGRAM_BOT_TOKEN": "test-token",
    "ADMIN_TELEGRAM_ID": "999",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "test-key",
    "GEMINI_API_KEY": "test-gemini-key",
    "GEMINI_MODEL": "gemini-2.5-flash",
    "JWT_SECRET_KEY": "test-jwt-secret",
}

_EMPTY_CONTEXT = {
    "period": "2026-06",
    "period_start": "2026-06-01",
    "period_end": "2026-07-01",
    "income_total": 100000.0,
    "expense_total": 5000.0,
    "net_cashflow": 95000.0,
    "surplus_rate_percent": 95.0,
    "period_elapsed_days": 29,
    "period_total_days": 30,
    "period_remaining_days": 1,
    "period_progress_percent": 96.67,
    "average_daily_expense_so_far": 172.41,
    "average_daily_variable_expense_so_far": 172.41,
    "projected_expense_total_at_current_pace": 5172.41,
    "projected_net_cashflow_at_current_pace": 94827.59,
    "projected_surplus_rate_percent": 94.83,
    "top_categories": [],
    "budget_violations": [],
    "recurring_expenses": [],
    "expense_cadence_breakdown": {
        "likely_monthly_or_fixed": [],
        "likely_daily_or_variable": [],
        "unclear_or_one_off": [],
    },
    "last_3_months": [],
}


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def seed_transaction(repository: TransactionsRepository) -> None:
    repository.create(
        user_id="user-1",
        transaction_type="expense",
        name="Parkir",
        category="transportasi",
        amount=Decimal("5000"),
        transaction_date=date(2026, 6, 26),
        source="manual",
        parser="manual",
    )
    repository.create(
        user_id="user-1",
        transaction_type="income",
        name="Gaji",
        category="pendapatan",
        amount=Decimal("100000"),
        transaction_date=date(2026, 6, 26),
        source="manual",
        parser="manual",
    )


@patch.dict("os.environ", _FAKE_ENV)
@patch("google.genai.Client")
async def test_advisor_insights_reuses_cached_result_for_same_context(
    mock_client_cls: MagicMock,
) -> None:
    supabase = FakeSupabaseClient()
    transactions = TransactionsRepository(supabase)
    budgets = BudgetsRepository(supabase)
    insights = InsightsRepository(supabase)
    seed_transaction(transactions)

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed = {
        "summary": "Surplus masih sementara.",
        "recommendations": ["Pantau pengeluaran harian."],
        "warnings": ["Periode masih berjalan."],
    }
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    mock_client_cls.return_value = mock_client

    app.dependency_overrides[get_current_user] = lambda: _CURRENT_USER
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(
        gemini_api_key="test-key",
        gemini_model="test-model",
    )
    app.dependency_overrides[get_transactions_repository] = lambda: transactions
    app.dependency_overrides[get_budgets_repository] = lambda: budgets
    app.dependency_overrides[get_insights_repository] = lambda: insights

    with patch(
        "app.services.advisor_service.current_cashflow_period",
        return_value=(date(2026, 6, 1), date(2026, 7, 1)),
    ), patch(
        "app.services.advisor_service.today_jakarta",
        return_value=date(2026, 6, 29),
    ):
        client = TestClient(app)
        try:
            first_response = client.post("/advisor/insights")
            second_response = client.post("/advisor/insights")
        finally:
            clear_overrides()

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()
    assert first_response.json() == {
        "summary": "Surplus masih sementara.",
        "recommendations": ["Pantau pengeluaran harian."],
        "warnings": ["Periode masih berjalan."],
    }
    assert mock_client.aio.models.generate_content.await_count == 1


@patch.dict("os.environ", _FAKE_ENV)
@patch("google.genai.Client")
async def test_advisor_insights_regenerates_after_financial_data_changes(
    mock_client_cls: MagicMock,
) -> None:
    supabase = FakeSupabaseClient()
    transactions = TransactionsRepository(supabase)
    budgets = BudgetsRepository(supabase)
    insights = InsightsRepository(supabase)
    seed_transaction(transactions)

    mock_client = MagicMock()
    first_response = MagicMock()
    first_response.parsed = {
        "summary": "Insight awal.",
        "recommendations": ["Pantau pengeluaran."],
        "warnings": [],
    }
    second_response = MagicMock()
    second_response.parsed = {
        "summary": "Insight setelah data berubah.",
        "recommendations": ["Kurangi makan di luar."],
        "warnings": ["Pengeluaran bertambah."],
    }
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=[first_response, second_response],
    )
    mock_client_cls.return_value = mock_client

    app.dependency_overrides[get_current_user] = lambda: _CURRENT_USER
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(
        gemini_api_key="test-key",
        gemini_model="test-model",
    )
    app.dependency_overrides[get_transactions_repository] = lambda: transactions
    app.dependency_overrides[get_budgets_repository] = lambda: budgets
    app.dependency_overrides[get_insights_repository] = lambda: insights

    with patch(
        "app.services.advisor_service.current_cashflow_period",
        return_value=(date(2026, 6, 1), date(2026, 7, 1)),
    ), patch(
        "app.services.advisor_service.today_jakarta",
        return_value=date(2026, 6, 29),
    ):
        client = TestClient(app)
        try:
            first = client.post("/advisor/insights")
            transactions.create(
                user_id="user-1",
                transaction_type="expense",
                name="Makan",
                category="makanan_minuman",
                amount=Decimal("25000"),
                transaction_date=date(2026, 6, 29),
                source="manual",
                parser="manual",
            )
            second = client.post("/advisor/insights")
        finally:
            clear_overrides()

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["summary"] == "Insight awal."
    assert second.json()["summary"] == "Insight setelah data berubah."
    assert mock_client.aio.models.generate_content.await_count == 2


@patch.dict("os.environ", _FAKE_ENV)
async def test_build_advisor_context_aggregates_current_user_data() -> None:
    transactions = TransactionsRepository(FakeSupabaseClient())
    budgets = BudgetsRepository(FakeSupabaseClient())
    seed_transaction(transactions)
    budgets.create("user-1", "transportasi", Decimal("50000"), date(2026, 6, 1))

    with patch(
        "app.services.advisor_service.current_cashflow_period",
        return_value=(date(2026, 6, 1), date(2026, 7, 1)),
    ), patch(
        "app.services.advisor_service.today_jakarta",
        return_value=date(2026, 6, 29),
    ):
        context = build_advisor_context("user-1", transactions, budgets)

    assert context["expense_total"] == 5000.0
    assert context["income_total"] == 100000.0
    assert context["net_cashflow"] == 95000.0
    assert context["surplus_rate_percent"] == 95.0
    assert "savings_rate_percent" not in context
    assert context["period_total_days"] == 30
    assert context["period_remaining_days"] == 1
    assert context["expense_cadence_breakdown"]["likely_daily_or_variable"] == [
        {
            "category": "transportasi",
            "amount": 5000.0,
            "transaction_count": 1,
            "reason": "kategori pengeluaran harian/variabel",
        }
    ]
    assert len(context["budget_violations"]) == 0


@patch.dict("os.environ", _FAKE_ENV)
async def test_build_advisor_context_uses_custom_cashflow_period() -> None:
    transactions = TransactionsRepository(FakeSupabaseClient())
    budgets = BudgetsRepository(FakeSupabaseClient())
    transactions.create(
        user_id="user-1",
        transaction_type="income",
        name="Gaji",
        category="pendapatan",
        amount=Decimal("100000"),
        transaction_date=date(2026, 6, 29),
        source="manual",
        parser="manual",
    )
    transactions.create(
        user_id="user-1",
        transaction_type="expense",
        name="Makan",
        category="makanan_minuman",
        amount=Decimal("25000"),
        transaction_date=date(2026, 7, 1),
        source="manual",
        parser="manual",
    )
    transactions.create(
        user_id="user-1",
        transaction_type="expense",
        name="Lama",
        category="transportasi",
        amount=Decimal("999999"),
        transaction_date=date(2026, 6, 28),
        source="manual",
        parser="manual",
    )
    budgets.create(
        "user-1",
        "makanan_minuman",
        Decimal("20000"),
        date(2026, 6, 29),
    )

    with patch(
        "app.services.advisor_service.current_cashflow_period",
        return_value=(date(2026, 6, 29), date(2026, 7, 29)),
    ), patch(
        "app.services.advisor_service.today_jakarta",
        return_value=date(2026, 6, 29),
    ):
        context = build_advisor_context(
            "user-1",
            transactions,
            budgets,
            cashflow_period_start_day=29,
        )

    assert context["period"] == "2026-06-29"
    assert context["period_start"] == "2026-06-29"
    assert context["period_end"] == "2026-07-29"
    assert context["income_total"] == 100000.0
    assert context["expense_total"] == 25000.0
    assert context["net_cashflow"] == 75000.0
    assert context["surplus_rate_percent"] == 75.0
    assert context["period_elapsed_days"] == 1
    assert context["period_total_days"] == 30
    assert context["period_remaining_days"] == 29
    assert context["projected_expense_total_at_current_pace"] == 750000.0
    assert context["projected_net_cashflow_at_current_pace"] == -650000.0
    assert context["projected_surplus_rate_percent"] == -650.0
    assert context["budget_violations"] == [
        {"category": "makanan_minuman", "budget": 20000.0, "actual": 25000.0}
    ]


@patch.dict("os.environ", _FAKE_ENV)
async def test_system_instruction_prohibits_investment_advice() -> None:
    """The system instruction must prohibit investment, crypto, and stock advice."""
    instruction = _SYSTEM_INSTRUCTION.lower()
    assert "do not" in instruction
    assert any(
        term in instruction
        for term in ["stock", "saham", "crypto", "bond", "insurance"]
    )


@patch.dict("os.environ", _FAKE_ENV)
@patch("google.genai.Client")
async def test_generate_insights_returns_structured_report(
    mock_client_cls: MagicMock,
) -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed = {
        "summary": "Keuangan kamu sehat.",
        "recommendations": ["Terus catat pengeluaran."],
        "warnings": [],
    }
    mock_client.aio.models.generate_content = AsyncMock(
        return_value=mock_response,
    )
    mock_client_cls.return_value = mock_client

    with patch(
        "app.services.advisor_service.today_jakarta",
        return_value=date(2026, 6, 29),
    ):
        result = await generate_insights(_EMPTY_CONTEXT, "test-key", "test-model")

    call = mock_client.aio.models.generate_content.call_args
    assert "Today date: 2026-06-29" in call.kwargs["contents"]
    assert "Current period: 2026-06" in call.kwargs["contents"]
    assert "surplus_rate_percent" in call.kwargs["contents"]
    assert "savings_rate_percent" not in call.kwargs["contents"]
    assert "not savings" in call.kwargs["config"].system_instruction.lower()
    assert result["summary"] == "Keuangan kamu sehat."
    assert "Terus catat pengeluaran." in result["recommendations"]


@patch.dict("os.environ", _FAKE_ENV)
@patch("google.genai.Client")
async def test_generate_chat_answer_uses_context(
    mock_client_cls: MagicMock,
) -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = (
        "Berdasarkan data kamu, surplus bulanan sekitar Rp95.000."
    )
    mock_client.aio.models.generate_content = AsyncMock(
        return_value=mock_response,
    )
    mock_client_cls.return_value = mock_client

    with patch(
        "app.services.advisor_service.today_jakarta",
        return_value=date(2026, 6, 29),
    ):
        answer = await generate_chat_answer(
            _EMPTY_CONTEXT,
            "Bagaimana cashflow saya?",
            "test-key",
            "test-model",
        )

    call = mock_client.aio.models.generate_content.call_args
    assert "Today date: 2026-06-29" in call.kwargs["contents"]
    assert "Current period: 2026-06" in call.kwargs["contents"]
    assert "Rp95.000" in answer
