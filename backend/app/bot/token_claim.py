import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from app.bot import responses
from app.repositories.pending_token_claims_repository import (
    PendingTokenClaimsRepository,
)
from app.repositories.registration_tokens_repository import (
    CLAIM_ERROR_ALREADY_CLAIMED,
    CLAIM_ERROR_EXPIRED,
    CLAIM_ERROR_NOT_FOUND,
    RegistrationTokensRepository,
)
from app.repositories.users_repository import UsersRepository
from app.services.token_service import is_valid_token_format

logger = logging.getLogger(__name__)

TOKEN_CLAIM_CALLBACK = "token_claim"


class TelegramMessageSender(Protocol):
    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict | None = None,
    ) -> Any: ...


class TelegramCallbackClient(Protocol):
    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str | None = None,
    ) -> Any: ...

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict | None = None,
    ) -> Any: ...


def token_claim_inline_keyboard() -> dict:
    """Inline keyboard with a single button that triggers the token-claim flow."""
    return {
        "inline_keyboard": [
            [
                {
                    "text": responses.TOKEN_PROMPT_BUTTON,
                    "callback_data": TOKEN_CLAIM_CALLBACK,
                }
            ]
        ]
    }


async def handle_token_claim(
    text: str | None,
    telegram_user_id: int,
    chat_id: int,
    users_repository: UsersRepository,
    pending_claims_repository: PendingTokenClaimsRepository,
    registration_tokens_repository: RegistrationTokensRepository,
    telegram_client: TelegramMessageSender,
    claim_timeout_minutes: int,
    admin_contact_telegram: str = "",
    admin_contact_whatsapp: str = "",
    telegram_username: str | None = None,
    language_code: str = "id",
    currency: str = "IDR",
    timezone: str = "Asia/Jakarta",
) -> bool:
    """Handle the token-based self-registration flow for unregistered users.

    Returns ``True`` if the message was handled (token-related), ``False`` if
    the caller should continue to the normal rejection path.

    Flow:
      1. User sends ``/start``  → create a pending claim, reply with the token
         prompt and an inline button.
      2. User clicks the inline button  → refresh the pending claim and prompt
         the user to send their token.
      3. User sends a message while a pending claim is active  → treat it as a
         token and attempt to claim it.
    """
    user = users_repository.get_by_telegram_user_id(telegram_user_id)
    if user is not None and user.get("status") == "active":
        return False

    message_text = (text or "").strip()
    is_start = message_text.lower() == "/start"

    if is_start:
        expires_at = datetime.now(UTC) + timedelta(minutes=claim_timeout_minutes)
        pending_claims_repository.upsert(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            expires_at=expires_at,
        )
        await telegram_client.send_message(
            chat_id,
            responses.token_claim_prompt(
                telegram_user_id,
                admin_contact_telegram,
                admin_contact_whatsapp,
            ),
            reply_markup=token_claim_inline_keyboard(),
        )
        return True

    pending_claim = pending_claims_repository.get_active(telegram_user_id)
    if pending_claim is None:
        expired_claim = pending_claims_repository.get_for_telegram_user_id(
            telegram_user_id,
        )
        if expired_claim is not None:
            pending_claims_repository.delete(telegram_user_id)
            await telegram_client.send_message(chat_id, responses.TOKEN_PROMPT_EXPIRED)
            return True
        return False

    if not is_valid_token_format(message_text):
        await telegram_client.send_message(
            chat_id,
            responses.TOKEN_CLAIM_PENDING_BUT_NOT_TOKEN,
        )
        return True

    result = registration_tokens_repository.claim(
        token=message_text,
        telegram_user_id=telegram_user_id,
        telegram_username=telegram_username,
        language_code=language_code,
        currency=currency,
        timezone=timezone,
    )

    if result.get("ok"):
        pending_claims_repository.delete(telegram_user_id)
        await telegram_client.send_message(chat_id, responses.TOKEN_CLAIM_ACTIVE)
        return True

    error = result.get("error", CLAIM_ERROR_NOT_FOUND)
    if error == CLAIM_ERROR_EXPIRED:
        await telegram_client.send_message(chat_id, responses.TOKEN_EXPIRED)
    elif error == CLAIM_ERROR_ALREADY_CLAIMED:
        await telegram_client.send_message(chat_id, responses.TOKEN_ALREADY_CLAIMED)
    else:
        await telegram_client.send_message(chat_id, responses.TOKEN_INVALID)
    return True


async def handle_token_claim_callback(
    callback_query_id: str,
    telegram_user_id: int,
    chat_id: int,
    pending_claims_repository: PendingTokenClaimsRepository,
    telegram_client: TelegramCallbackClient,
    claim_timeout_minutes: int,
) -> bool:
    """Handle the inline-button callback for the token-claim flow.

    Refreshes the pending claim and asks the user to send their token.
    """
    expires_at = datetime.now(UTC) + timedelta(minutes=claim_timeout_minutes)
    pending_claims_repository.upsert(
        telegram_user_id=telegram_user_id,
        chat_id=chat_id,
        expires_at=expires_at,
    )
    await telegram_client.answer_callback_query(
        callback_query_id,
        text="Silakan kirim token pendaftaran kamu.",
    )
    await telegram_client.send_message(
        chat_id,
        "Kirimkan tokennya sekarang ya, contoh format: K7M2-PQ9X-AB43",
    )
    return True