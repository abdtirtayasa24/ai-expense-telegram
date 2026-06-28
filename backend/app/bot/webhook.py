import logging
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from app.bot.commands import handle_admin_command
from app.bot.onboarding import handle_registered_user_message
from app.integrations.telegram_client import TelegramClient
from app.repositories.advisor_chat_repository import AdvisorChatRepository
from app.repositories.budgets_repository import BudgetsRepository
from app.repositories.conversation_states_repository import ConversationStatesRepository
from app.repositories.transactions_repository import TransactionsRepository
from app.repositories.users_repository import UsersRepository

router = APIRouter()
logger = logging.getLogger(__name__)


class TelegramWebhookResponse(BaseModel):
    ok: bool


def get_settings():
    from app.core.config import settings

    return settings


def get_users_repository() -> UsersRepository:
    return UsersRepository()


def get_transactions_repository() -> TransactionsRepository:
    return TransactionsRepository()


def get_budgets_repository() -> BudgetsRepository:
    return BudgetsRepository()


def get_conversation_states_repository() -> ConversationStatesRepository:
    return ConversationStatesRepository()


def get_advisor_chat_repository() -> AdvisorChatRepository:
    return AdvisorChatRepository()


def get_telegram_client(
    settings: Annotated[Any, Depends(get_settings)],
) -> TelegramClient:
    return TelegramClient(settings.telegram_bot_token)


@router.post("/telegram", response_model=TelegramWebhookResponse)
async def telegram_webhook(
    update: dict[str, Any],
    background_tasks: BackgroundTasks,
    settings: Annotated[Any, Depends(get_settings)],
    users_repository: Annotated[UsersRepository, Depends(get_users_repository)],
    transactions_repository: Annotated[
        TransactionsRepository,
        Depends(get_transactions_repository),
    ],
    budgets_repository: Annotated[BudgetsRepository, Depends(get_budgets_repository)],
    conversation_states_repository: Annotated[
        ConversationStatesRepository,
        Depends(get_conversation_states_repository),
    ],
    advisor_chat_repository: Annotated[
        AdvisorChatRepository,
        Depends(get_advisor_chat_repository),
    ],
    telegram_client: Annotated[TelegramClient, Depends(get_telegram_client)],
) -> TelegramWebhookResponse:
    message = update.get("message")
    if not isinstance(message, dict):
        return TelegramWebhookResponse(ok=True)

    text = message.get("text")
    from_user = message.get("from")
    chat = message.get("chat")
    if not isinstance(text, str) or not isinstance(from_user, dict):
        return TelegramWebhookResponse(ok=True)
    if not isinstance(chat, dict):
        return TelegramWebhookResponse(ok=True)

    sender_telegram_user_id = from_user.get("id")
    chat_id = chat.get("id")
    if not isinstance(sender_telegram_user_id, int) or not isinstance(chat_id, int):
        return TelegramWebhookResponse(ok=True)

    background_tasks.add_task(
        process_telegram_message,
        text=text,
        sender_telegram_user_id=sender_telegram_user_id,
        chat_id=chat_id,
        admin_telegram_id=settings.admin_telegram_id,
        users_repository=users_repository,
        transactions_repository=transactions_repository,
        telegram_client=telegram_client,
        parser_confidence_threshold=settings.parser_confidence_threshold,
        budgets_repository=budgets_repository,
        conversation_states_repository=conversation_states_repository,
        advisor_chat_repository=advisor_chat_repository,
        gemini_api_key=getattr(settings, "gemini_api_key", None),
        gemini_model=getattr(settings, "gemini_model", None),
        advisor_mode_timeout_minutes=getattr(
            settings,
            "advisor_mode_timeout_minutes",
            15,
        ),
        advisor_chat_history_limit=getattr(settings, "advisor_chat_history_limit", 60),
    )
    return TelegramWebhookResponse(ok=True)


async def process_telegram_message(
    text: str,
    sender_telegram_user_id: int,
    chat_id: int,
    admin_telegram_id: int,
    users_repository: UsersRepository,
    transactions_repository: TransactionsRepository,
    telegram_client: TelegramClient,
    parser_confidence_threshold: float,
    budgets_repository: BudgetsRepository | None = None,
    conversation_states_repository: ConversationStatesRepository | None = None,
    advisor_chat_repository: AdvisorChatRepository | None = None,
    gemini_api_key: str | None = None,
    gemini_model: str | None = None,
    advisor_mode_timeout_minutes: int = 15,
    advisor_chat_history_limit: int = 60,
) -> None:
    try:
        handled = await handle_admin_command(
            text=text,
            sender_telegram_user_id=sender_telegram_user_id,
            chat_id=chat_id,
            admin_telegram_id=admin_telegram_id,
            users_repository=users_repository,
            telegram_client=telegram_client,
        )
        if handled:
            return
        await handle_registered_user_message(
            text=text,
            telegram_user_id=sender_telegram_user_id,
            chat_id=chat_id,
            users_repository=users_repository,
            transactions_repository=transactions_repository,
            telegram_client=telegram_client,
            parser_confidence_threshold=parser_confidence_threshold,
            budgets_repository=budgets_repository,
            conversation_states_repository=conversation_states_repository,
            advisor_chat_repository=advisor_chat_repository,
            gemini_api_key=gemini_api_key,
            gemini_model=gemini_model,
            advisor_mode_timeout_minutes=advisor_mode_timeout_minutes,
            advisor_chat_history_limit=advisor_chat_history_limit,
        )
    except Exception:
        logger.exception("Failed to process Telegram webhook update.")
