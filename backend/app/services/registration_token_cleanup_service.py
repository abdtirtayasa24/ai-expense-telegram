import logging
from typing import Any

from app.repositories.pending_token_claims_repository import (
    PendingTokenClaimsRepository,
)
from app.repositories.registration_tokens_repository import RegistrationTokensRepository

logger = logging.getLogger(__name__)


def cleanup_expired_registration_tokens(
    registration_tokens_repository: RegistrationTokensRepository,
    pending_token_claims_repository: PendingTokenClaimsRepository,
    mark_limit: int = 200,
    delete_limit: int = 200,
) -> dict[str, Any]:
    """Mark expired registration tokens and delete expired pending claims.

    Returns a dict with ``tokens_marked`` and ``claims_deleted`` counts.  Unlike
    the advisor-mode timeout job, this job does not send Telegram messages — it
    is purely a database cleanup that flips stale ``active`` tokens to
    ``expired`` and removes past-expiry pending claims.
    """
    tokens_marked = registration_tokens_repository.mark_expired(limit=mark_limit)
    claims_deleted = pending_token_claims_repository.delete_expired(limit=delete_limit)
    logger.info(
        "Expired token cleanup: marked %d tokens, deleted %d pending claims.",
        tokens_marked,
        claims_deleted,
    )
    return {"tokens_marked": tokens_marked, "claims_deleted": claims_deleted}