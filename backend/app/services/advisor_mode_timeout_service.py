import logging
from datetime import UTC, datetime
from typing import Any

from app.bot.advisor import ADVISOR_MODE_STATE
from app.bot.responses import ADVISOR_MODE_TIMEOUT_NOTICE
from app.integrations.telegram_client import TelegramClient
from app.repositories.conversation_states_repository import ConversationStatesRepository

logger = logging.getLogger(__name__)


def _chat_id_from_payload(payload: Any) -> int | None:
    if not isinstance(payload, dict):
        return None
    chat_id = payload.get("chat_id")
    if isinstance(chat_id, int):
        return chat_id
    return None


async def notify_expired_advisor_modes(
    conversation_states_repository: ConversationStatesRepository,
    telegram_client: TelegramClient,
    limit: int = 100,
) -> int:
    states = conversation_states_repository.claim_expired_by_state(
        ADVISOR_MODE_STATE,
        limit=limit,
    )
    notified = 0
    for state in states:
        latest_state = conversation_states_repository.get_latest_for_user(
            state["user_id"],
            ADVISOR_MODE_STATE,
        )
        if latest_state is None or latest_state.get("id") != state.get("id"):
            conversation_states_repository.delete_for_user(
                state["id"],
                state["user_id"],
            )
            continue
        if not _is_expired(latest_state):
            continue

        chat_id = _chat_id_from_payload(state.get("payload"))
        if chat_id is None:
            conversation_states_repository.delete_for_user(
                state["id"],
                state["user_id"],
            )
            continue

        try:
            await telegram_client.send_message(chat_id, ADVISOR_MODE_TIMEOUT_NOTICE)
        except Exception:
            logger.exception("Failed to send advisor mode timeout notification.")
            continue

        if conversation_states_repository.delete_for_user(
            state["id"],
            state["user_id"],
        ):
            notified += 1
    return notified


def _is_expired(state: dict[str, Any]) -> bool:
    expires_at = datetime.fromisoformat(str(state["expires_at"]))
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= datetime.now(UTC)
