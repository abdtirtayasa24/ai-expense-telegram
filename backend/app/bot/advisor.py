import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from app.bot import responses
from app.repositories.advisor_chat_repository import AdvisorChatRepository
from app.repositories.base import Row
from app.repositories.budgets_repository import BudgetsRepository
from app.repositories.conversation_states_repository import ConversationStatesRepository
from app.repositories.transactions_repository import TransactionsRepository
from app.services.advisor_chat_service import (
    advisor_mode_payload,
    answer_advisor_question,
)

ADVISOR_MODE_STATE = "advisor_mode"
logger = logging.getLogger(__name__)


class TelegramMessageSender(Protocol):
    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict | None = None,
    ) -> Any: ...


async def handle_advisor_mode_message(
    text: str,
    user: Row,
    chat_id: int,
    telegram_client: TelegramMessageSender,
    transactions_repository: TransactionsRepository,
    budgets_repository: BudgetsRepository,
    conversation_states_repository: ConversationStatesRepository,
    advisor_chat_repository: AdvisorChatRepository,
    gemini_api_key: str,
    gemini_model: str,
    timeout_minutes: int,
    history_limit: int,
) -> bool:
    command = _command(text)
    if command == "/advisor":
        _upsert_advisor_mode(
            user,
            chat_id,
            conversation_states_repository,
            timeout_minutes,
        )
        await telegram_client.send_message(chat_id, responses.ADVISOR_MODE_ACTIVE)
        return True

    if command == "/transaction":
        state = conversation_states_repository.get_latest_for_user(
            user["id"],
            ADVISOR_MODE_STATE,
        )
        if state is not None:
            conversation_states_repository.delete_for_user(state["id"], user["id"])
        await telegram_client.send_message(chat_id, responses.TRANSACTION_MODE_ACTIVE)
        return True

    state = conversation_states_repository.get_latest_for_user(
        user["id"],
        ADVISOR_MODE_STATE,
    )
    if state is None:
        return False

    if _is_expired(state):
        conversation_states_repository.delete_for_user(state["id"], user["id"])
        await telegram_client.send_message(chat_id, responses.ADVISOR_MODE_EXPIRED)
        return True

    try:
        answer = await answer_advisor_question(
            user_id=user["id"],
            message=text,
            source="telegram_chat",
            transactions_repository=transactions_repository,
            budgets_repository=budgets_repository,
            advisor_chat_repository=advisor_chat_repository,
            api_key=gemini_api_key,
            model=gemini_model,
            history_limit=history_limit,
        )
    except Exception:
        logger.exception("Advisor chat failed.")
        await telegram_client.send_message(chat_id, responses.ADVISOR_UNAVAILABLE)
        return True
    _refresh_advisor_mode(
        state,
        user,
        chat_id,
        conversation_states_repository,
        timeout_minutes,
    )
    await telegram_client.send_message(chat_id, answer)
    return True


def _command(text: str) -> str:
    parts = text.strip().split()
    if not parts:
        return ""
    return parts[0].split("@", maxsplit=1)[0].lower()


def _expires_at(timeout_minutes: int) -> datetime:
    return datetime.now(UTC) + timedelta(minutes=timeout_minutes)


def _upsert_advisor_mode(
    user: Row,
    chat_id: int,
    repository: ConversationStatesRepository,
    timeout_minutes: int,
) -> None:
    state = repository.get_latest_for_user(user["id"], ADVISOR_MODE_STATE)
    payload = advisor_mode_payload(chat_id)
    expires_at = _expires_at(timeout_minutes)
    if state is None:
        repository.create(
            user_id=user["id"],
            state=ADVISOR_MODE_STATE,
            payload=payload,
            expires_at=expires_at,
        )
        return
    repository.update_for_user(
        state["id"],
        user["id"],
        {"payload": payload, "expires_at": expires_at},
    )


def _refresh_advisor_mode(
    state: Row,
    user: Row,
    chat_id: int,
    repository: ConversationStatesRepository,
    timeout_minutes: int,
) -> None:
    repository.update_for_user(
        state["id"],
        user["id"],
        {
            "payload": advisor_mode_payload(chat_id),
            "expires_at": _expires_at(timeout_minutes),
        },
    )


def _is_expired(state: Row) -> bool:
    expires_at = datetime.fromisoformat(str(state["expires_at"]))
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= datetime.now(UTC)
