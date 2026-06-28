"""Advisor guardrail tests — verify prohibited advice is rejected and
supported advice is answered with user-data grounding."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.repositories.budgets_repository import BudgetsRepository
from app.repositories.transactions_repository import TransactionsRepository
from app.services.advisor_service import (
    _SYSTEM_INSTRUCTION,
    build_advisor_context,
    generate_chat_answer,
    generate_insights,
)
from tests.test_repositories import FakeSupabaseClient

pytestmark = pytest.mark.asyncio

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
    "income_total": 100000.0,
    "expense_total": 5000.0,
    "net_cashflow": 95000.0,
    "savings_rate_percent": 95.0,
    "top_categories": [],
    "budget_violations": [],
    "recurring_expenses": [],
    "last_3_months": [],
}


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
async def test_build_advisor_context_aggregates_current_user_data() -> None:
    transactions = TransactionsRepository(FakeSupabaseClient())
    budgets = BudgetsRepository(FakeSupabaseClient())
    seed_transaction(transactions)
    budgets.create("user-1", "transportasi", Decimal("50000"), date(2026, 6, 1))

    context = build_advisor_context("user-1", transactions, budgets)

    assert context["expense_total"] == 5000.0
    assert context["income_total"] == 100000.0
    assert context["net_cashflow"] == 95000.0
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

    result = await generate_insights(_EMPTY_CONTEXT, "test-key", "test-model")
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

    answer = await generate_chat_answer(
        _EMPTY_CONTEXT,
        "Bagaimana cashflow saya?",
        "test-key",
        "test-model",
    )
    assert "Rp95.000" in answer
