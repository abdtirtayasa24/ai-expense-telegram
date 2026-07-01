import secrets
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.api.dependencies import get_conversation_states_repository, get_settings
from app.integrations.telegram_client import TelegramClient
from app.repositories.conversation_states_repository import ConversationStatesRepository
from app.repositories.pending_token_claims_repository import (
    PendingTokenClaimsRepository,
)
from app.repositories.registration_tokens_repository import RegistrationTokensRepository
from app.services.advisor_mode_timeout_service import notify_expired_advisor_modes
from app.services.registration_token_cleanup_service import (
    cleanup_expired_registration_tokens,
)

router = APIRouter()


class AdvisorModeTimeoutsResponse(BaseModel):
    ok: bool
    notified: int


class ExpiredTokenCleanupResponse(BaseModel):
    ok: bool
    tokens_marked: int
    claims_deleted: int


def get_telegram_client(
    settings: Annotated[Any, Depends(get_settings)],
) -> TelegramClient:
    return TelegramClient(settings.telegram_bot_token)


def get_registration_tokens_repository() -> RegistrationTokensRepository:
    return RegistrationTokensRepository()


def get_pending_token_claims_repository() -> PendingTokenClaimsRepository:
    return PendingTokenClaimsRepository()


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


@router.post(
    "/jobs/expired-token-cleanup",
    response_model=ExpiredTokenCleanupResponse,
)
async def expired_token_cleanup_job(
    settings: Annotated[Any, Depends(get_settings)],
    registration_tokens_repository: Annotated[
        RegistrationTokensRepository,
        Depends(get_registration_tokens_repository),
    ],
    pending_token_claims_repository: Annotated[
        PendingTokenClaimsRepository,
        Depends(get_pending_token_claims_repository),
    ],
    x_cron_secret: Annotated[str | None, Header(alias="X-Cron-Secret")] = None,
) -> ExpiredTokenCleanupResponse:
    if not settings.cron_secret or not x_cron_secret or not secrets.compare_digest(
        x_cron_secret,
        settings.cron_secret,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cron secret tidak valid.",
        )

    result = cleanup_expired_registration_tokens(
        registration_tokens_repository,
        pending_token_claims_repository,
    )
    return ExpiredTokenCleanupResponse(
        ok=True,
        tokens_marked=result["tokens_marked"],
        claims_deleted=result["claims_deleted"],
    )
