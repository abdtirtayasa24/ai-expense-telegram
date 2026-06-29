from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.parser import ParsedTransaction

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


def make_parsed_transaction(
    *,
    name: str = "Parkir",
    amount: Decimal | None = Decimal("5000"),
    transaction_type: str = "expense",
    category: str = "transportasi",
    transaction_date: date | None = None,
    parser: str = "gemini",
    confidence_score: float = 0.9,
    needs_clarification: bool = False,
    clarification_question: str | None = None,
) -> ParsedTransaction:
    return ParsedTransaction(
        name=name,
        amount=amount,
        type=transaction_type,  # type: ignore[arg-type]
        category=category,  # type: ignore[arg-type]
        transaction_date=transaction_date or date(2026, 6, 27),
        parser=parser,  # type: ignore[arg-type]
        confidence_score=confidence_score,
        needs_clarification=needs_clarification,
        clarification_question=clarification_question,
    )


class FakeTransactionsRepository:
    def __init__(self) -> None:
        self.transactions: list[dict[str, Any]] = []

    def create(self, **payload: Any) -> dict[str, Any]:
        row: dict[str, Any] = {
            "id": f"tx-{len(self.transactions) + 1}",
            **payload,
        }
        self.transactions.append(row)
        return row


class FakeTelegramClient:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict | None = None,
    ) -> dict[str, bool]:
        self.messages.append((chat_id, text))
        return {"ok": True}


_DEFAULT_USER: dict[str, Any] = {"id": "user-111"}


# ---------------------------------------------------------------------------
# 1. Tracer bullet: Gemini returns valid ParsedTransaction
# ---------------------------------------------------------------------------

@patch.dict("os.environ", _FAKE_ENV)
@patch("google.genai.Client")
async def test_gemini_parser_returns_valid_transaction(
    mock_client_cls: MagicMock,
) -> None:
    from app.services.gemini_parser import parse_gemini_transaction

    expected = make_parsed_transaction()

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed = expected
    mock_client.aio.models.generate_content = AsyncMock(
        return_value=mock_response,
    )
    mock_client_cls.return_value = mock_client

    result = await parse_gemini_transaction("Parkir 5000", date(2026, 6, 27))

    assert isinstance(result, ParsedTransaction)
    assert result.name == "Parkir"
    assert result.amount == Decimal("5000")
    assert result.type == "expense"
    assert result.category == "transportasi"
    assert result.parser == "gemini"
    assert result.confidence_score == 0.9
    assert result.needs_clarification is False
    assert result.clarification_question is None


# ---------------------------------------------------------------------------
# 2. High-confidence rule parser skips Gemini entirely
# ---------------------------------------------------------------------------

@patch.dict("os.environ", _FAKE_ENV)
@patch("app.services.gemini_parser.parse_gemini_transaction")
async def test_high_confidence_rule_parser_skips_gemini(
    mock_gemini_parse: AsyncMock,
) -> None:
    from app.bot.transactions import handle_transaction_message

    repo = FakeTransactionsRepository()
    client = FakeTelegramClient()

    allowed = await handle_transaction_message(
        text="Bayar parkir 5000",
        user=_DEFAULT_USER,
        chat_id=1234,
        transactions_repository=repo,  # type: ignore[arg-type]
        telegram_client=client,
        parser_confidence_threshold=0.75,
    )

    assert allowed is True
    mock_gemini_parse.assert_not_called()
    assert repo.transactions
    assert repo.transactions[0]["parser"] == "rule_based"


# ---------------------------------------------------------------------------
# 3. Low-confidence rule parser calls Gemini, saves with parser=gemini
# ---------------------------------------------------------------------------

@patch.dict("os.environ", _FAKE_ENV)
@patch("app.services.gemini_parser.parse_gemini_transaction")
async def test_low_confidence_rule_parser_calls_gemini_fallback(
    mock_gemini_parse: AsyncMock,
) -> None:
    from app.bot.transactions import handle_transaction_message

    mock_gemini_parse.return_value = make_parsed_transaction()
    repo = FakeTransactionsRepository()
    client = FakeTelegramClient()

    allowed = await handle_transaction_message(
        text="foo 5000",
        user=_DEFAULT_USER,
        chat_id=1234,
        transactions_repository=repo,  # type: ignore[arg-type]
        telegram_client=client,
        parser_confidence_threshold=0.75,
    )

    assert allowed is True
    mock_gemini_parse.assert_called_once()
    assert repo.transactions[0]["parser"] == "gemini"
    # mock returns default name="Parkir" from make_parsed_transaction()
    assert repo.transactions[0]["name"] == "Parkir"


# ---------------------------------------------------------------------------
# 4. Gemini returns needs_clarification=true → ask user
# ---------------------------------------------------------------------------

@patch.dict("os.environ", _FAKE_ENV)
@patch("app.services.gemini_parser.parse_gemini_transaction")
async def test_gemini_needs_clarification_asks_user(
    mock_gemini_parse: AsyncMock,
) -> None:
    from app.bot.transactions import handle_transaction_message

    mock_gemini_parse.return_value = make_parsed_transaction(
        needs_clarification=True,
        clarification_question="Berapa nominalnya?",
        confidence_score=0.4,
    )
    repo = FakeTransactionsRepository()
    client = FakeTelegramClient()

    allowed = await handle_transaction_message(
        text="foo 5000",
        user=_DEFAULT_USER,
        chat_id=1234,
        transactions_repository=repo,  # type: ignore[arg-type]
        telegram_client=client,
        parser_confidence_threshold=0.75,
    )

    assert allowed is False
    assert repo.transactions == []
    assert len(client.messages) == 1
    assert "Berapa nominalnya?" in client.messages[0][1]


# ---------------------------------------------------------------------------
# 5. Gemini API error → ask clarification
# ---------------------------------------------------------------------------

@patch.dict("os.environ", _FAKE_ENV)
@patch("app.services.gemini_parser.parse_gemini_transaction")
async def test_gemini_api_error_asks_clarification(
    mock_gemini_parse: AsyncMock,
) -> None:
    from app.bot.transactions import handle_transaction_message

    mock_gemini_parse.side_effect = ValueError("Gemini API error")
    repo = FakeTransactionsRepository()
    client = FakeTelegramClient()

    allowed = await handle_transaction_message(
        text="foo 5000",
        user=_DEFAULT_USER,
        chat_id=1234,
        transactions_repository=repo,  # type: ignore[arg-type]
        telegram_client=client,
        parser_confidence_threshold=0.75,
    )

    assert allowed is False
    assert repo.transactions == []
    assert len(client.messages) == 1


# ---------------------------------------------------------------------------
# 6. Gemini returns invalid output → ask clarification
# ---------------------------------------------------------------------------

@patch.dict("os.environ", _FAKE_ENV)
@patch("app.services.gemini_parser.parse_gemini_transaction")
async def test_gemini_invalid_output_asks_clarification(
    mock_gemini_parse: AsyncMock,
) -> None:
    from app.bot.transactions import handle_transaction_message

    mock_gemini_parse.side_effect = TypeError("Invalid response format")
    repo = FakeTransactionsRepository()
    client = FakeTelegramClient()

    allowed = await handle_transaction_message(
        text="foo 5000",
        user=_DEFAULT_USER,
        chat_id=1234,
        transactions_repository=repo,  # type: ignore[arg-type]
        telegram_client=client,
        parser_confidence_threshold=0.75,
    )

    assert allowed is False
    assert repo.transactions == []
    assert len(client.messages) == 1