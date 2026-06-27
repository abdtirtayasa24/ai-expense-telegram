import logging
from decimal import Decimal
from typing import Any, Protocol

from app.bot import responses
from app.repositories.base import Row
from app.schemas.parser import ParsedTransaction
from app.services.rule_parser import parse_rule_based_transaction, today_jakarta

logger = logging.getLogger(__name__)


class TransactionCreator(Protocol):
    def create(
        self,
        user_id: str,
        transaction_type: str,
        name: str,
        category: str,
        amount: Decimal,
        transaction_date: Any,
        source: str,
        parser: str,
        note: str | None = None,
        confidence_score: float | None = None,
        raw_message: str | None = None,
    ) -> Row: ...


async def handle_transaction_message(
    text: str,
    user: Row,
    chat_id: int,
    transactions_repository: TransactionCreator,
    telegram_client: Any,
    parser_confidence_threshold: float,
) -> bool:
    parsed = parse_rule_based_transaction(text)
    if not should_ask_clarification(parsed, parser_confidence_threshold):
        if parsed.amount is not None and parsed.type is not None and parsed.amount > 0:
            transactions_repository.create(
                user_id=user["id"],
                transaction_type=parsed.type,
                name=parsed.name,
                category=parsed.category,
                amount=parsed.amount,
                transaction_date=parsed.transaction_date,
                source="telegram_chat",
                parser=parsed.parser,
                confidence_score=parsed.confidence_score,
                raw_message=text,
            )
            await telegram_client.send_message(
                chat_id,
                format_transaction_confirmation(parsed),
            )
            return True

    # Rule parser low-confidence → try Gemini fallback
    try:
        from app.services.gemini_parser import parse_gemini_transaction

        parsed = await parse_gemini_transaction(text, today_jakarta())
    except Exception:
        logger.exception("Gemini parser failed, asking clarification.")
        await telegram_client.send_message(chat_id, responses.PARSER_CLARIFICATION)
        return False

    if should_ask_clarification(parsed, parser_confidence_threshold):
        await telegram_client.send_message(
            chat_id,
            parsed.clarification_question or responses.PARSER_CLARIFICATION,
        )
        return False

    if parsed.amount is None or parsed.type is None or parsed.amount <= 0:
        await telegram_client.send_message(chat_id, responses.PARSER_CLARIFICATION)
        return False

    transactions_repository.create(
        user_id=user["id"],
        transaction_type=parsed.type,
        name=parsed.name,
        category=parsed.category,
        amount=parsed.amount,
        transaction_date=parsed.transaction_date,
        source="telegram_chat",
        parser=parsed.parser,
        confidence_score=parsed.confidence_score,
        raw_message=text,
    )
    await telegram_client.send_message(chat_id, format_transaction_confirmation(parsed))
    return True


def should_ask_clarification(
    parsed: ParsedTransaction,
    parser_confidence_threshold: float,
) -> bool:
    return parsed.needs_clarification or (
        parsed.confidence_score < parser_confidence_threshold
    )


def format_transaction_confirmation(parsed: ParsedTransaction) -> str:
    type_label = transaction_type_label(parsed.type)
    return (
        f"Oke, {type_label} {parsed.name.lower()} "
        f"{format_rupiah(parsed.amount or Decimal('0'))} sudah tercatat."
    )


def transaction_type_label(transaction_type: str | None) -> str:
    if transaction_type == "income":
        return "pemasukan"
    return "pengeluaran"


def format_rupiah(value: Decimal) -> str:
    amount = int(value)
    return f"Rp{amount:,}".replace(",", ".")
