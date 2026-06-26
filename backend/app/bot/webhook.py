import logging
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from app.bot.commands import handle_admin_command
from app.bot.onboarding import handle_registered_user_message
from app.integrations.telegram_client import TelegramClient
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
        )
    except Exception:
        logger.exception("Failed to process Telegram webhook update.")
