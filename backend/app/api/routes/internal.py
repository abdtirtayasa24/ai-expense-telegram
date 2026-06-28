import secrets
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.api.dependencies import get_conversation_states_repository, get_settings
from app.integrations.telegram_client import TelegramClient
from app.repositories.conversation_states_repository import ConversationStatesRepository
from app.services.advisor_mode_timeout_service import notify_expired_advisor_modes

router = APIRouter()


class AdvisorModeTimeoutsResponse(BaseModel):
    ok: bool
    notified: int


def get_telegram_client(
    settings: Annotated[Any, Depends(get_settings)],
) -> TelegramClient:
    return TelegramClient(settings.telegram_bot_token)


@router.post("/jobs/advisor-mode-timeouts", response_model=AdvisorModeTimeoutsResponse)
async def advisor_mode_timeouts_job(
    settings: Annotated[Any, Depends(get_settings)],
    conversation_states_repository: Annotated[
        ConversationStatesRepository,
        Depends(get_conversation_states_repository),
    ],
    telegram_client: Annotated[TelegramClient, Depends(get_telegram_client)],
    x_cron_secret: Annotated[str | None, Header(alias="X-Cron-Secret")] = None,
) -> AdvisorModeTimeoutsResponse:
    if not settings.cron_secret or not x_cron_secret or not secrets.compare_digest(
        x_cron_secret,
        settings.cron_secret,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cron secret tidak valid.",
        )

    notified = await notify_expired_advisor_modes(
        conversation_states_repository,
        telegram_client,
    )
    return AdvisorModeTimeoutsResponse(ok=True, notified=notified)
