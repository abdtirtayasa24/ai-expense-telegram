from typing import Any, Protocol

from app.bot import responses
from app.bot.advisor import handle_advisor_mode_message
from app.bot.transactions import TransactionCreator, handle_transaction_message
from app.repositories.advisor_chat_repository import AdvisorChatRepository
from app.repositories.base import Row
from app.repositories.budgets_repository import BudgetsRepository
from app.repositories.conversation_states_repository import ConversationStatesRepository
from app.repositories.users_repository import UsersRepository


class TelegramMessageSender(Protocol):
    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict | None = None,
    ) -> Any: ...


async def handle_registered_user_message(
    text: str,
    telegram_user_id: int,
    chat_id: int,
    users_repository: UsersRepository,
    telegram_client: TelegramMessageSender,
    transactions_repository: TransactionCreator,
    parser_confidence_threshold: float,
    budgets_repository: BudgetsRepository | None = None,
    conversation_states_repository: ConversationStatesRepository | None = None,
    advisor_chat_repository: AdvisorChatRepository | None = None,
    gemini_api_key: str | None = None,
    gemini_model: str | None = None,
    advisor_mode_timeout_minutes: int = 15,
    advisor_chat_history_limit: int = 60,
    admin_contact_telegram: str = "",
    admin_contact_whatsapp: str = "",
) -> bool:
    user = users_repository.get_by_telegram_user_id(telegram_user_id)
    if user is None or user.get("status") != "active":
        await telegram_client.send_message(
            chat_id,
            responses.user_not_active_with_contact(
                telegram_user_id,
                admin_contact_telegram,
                admin_contact_whatsapp,
            ),
        )
        return False

    onboarding_status = user.get("onboarding_status")
    if onboarding_status == "completed":
        if (
            budgets_repository is not None
            and conversation_states_repository is not None
            and advisor_chat_repository is not None
            and gemini_api_key is not None
            and gemini_model is not None
        ):
            advisor_handled = await handle_advisor_mode_message(
                text=text,
                user=user,
                chat_id=chat_id,
                telegram_client=telegram_client,
                transactions_repository=transactions_repository,  # type: ignore[arg-type]
                budgets_repository=budgets_repository,
                conversation_states_repository=conversation_states_repository,
                advisor_chat_repository=advisor_chat_repository,
                gemini_api_key=gemini_api_key,
                gemini_model=gemini_model,
                timeout_minutes=advisor_mode_timeout_minutes,
                history_limit=advisor_chat_history_limit,
            )
            if advisor_handled:
                return True

        return await handle_transaction_message(
            text=text,
            user=user,
            chat_id=chat_id,
            transactions_repository=transactions_repository,
            telegram_client=telegram_client,
            parser_confidence_threshold=parser_confidence_threshold,
        )

    if onboarding_status == "pending":
        users_repository.update_onboarding_status(user["id"], "asking_first_name")
        await telegram_client.send_message(chat_id, responses.ASK_FIRST_NAME)
        return False

    if onboarding_status == "asking_first_name":
        first_name = text.strip()
        if not is_valid_name(first_name):
            await telegram_client.send_message(chat_id, responses.INVALID_NAME)
            return False
        users_repository.update_profile(user["id"], first_name=first_name)
        users_repository.update_onboarding_status(user["id"], "asking_last_name")
        await telegram_client.send_message(chat_id, responses.ASK_LAST_NAME)
        return False

    if onboarding_status == "asking_last_name":
        last_name = text.strip()
        if not is_valid_name(last_name):
            await telegram_client.send_message(chat_id, responses.INVALID_NAME)
            return False
        updated_user = users_repository.update_profile(user["id"], last_name=last_name)
        users_repository.update_onboarding_status(user["id"], "completed")
        completed_user = (
            users_repository.get_by_telegram_user_id(telegram_user_id)
            or updated_user
            or user
        )
        first_name = _first_name(completed_user)
        await telegram_client.send_message(
            chat_id,
            responses.onboarding_completed(first_name),
        )
        return True

    users_repository.update_onboarding_status(user["id"], "asking_first_name")
    await telegram_client.send_message(chat_id, responses.ASK_FIRST_NAME)
    return False


def is_valid_name(value: str) -> bool:
    name = value.strip()
    if len(name) < 2 or len(name) > 50:
        return False
    return all(character.isalpha() or character in " '-" for character in name)


def _first_name(user: Row) -> str:
    first_name = (user.get("first_name") or "").strip()
    return first_name or "kamu"
