from typing import Any, Literal

from app.repositories.advisor_chat_repository import AdvisorChatRepository
from app.repositories.budgets_repository import BudgetsRepository
from app.repositories.transactions_repository import TransactionsRepository
from app.services.advisor_service import build_advisor_context, generate_chat_answer

AdvisorChatSource = Literal["telegram_chat", "mini_app"]


async def answer_advisor_question(
    user_id: str,
    message: str,
    source: AdvisorChatSource,
    transactions_repository: TransactionsRepository,
    budgets_repository: BudgetsRepository,
    advisor_chat_repository: AdvisorChatRepository,
    api_key: str,
    model: str,
    history_limit: int,
    cashflow_period_start_day: int = 1,
) -> str:
    history = advisor_chat_repository.list_recent_for_user(user_id, history_limit)
    context = build_advisor_context(
        user_id,
        transactions_repository,
        budgets_repository,
        cashflow_period_start_day=cashflow_period_start_day,
    )
    answer = await generate_chat_answer(
        context,
        message,
        api_key,
        model,
        chat_history=history,
    )
    advisor_chat_repository.create_message(
        user_id=user_id,
        role="user",
        content=message,
        source=source,
    )
    advisor_chat_repository.create_message(
        user_id=user_id,
        role="assistant",
        content=answer,
        source=source,
    )
    return answer


def advisor_mode_payload(chat_id: int) -> dict[str, Any]:
    return {"chat_id": chat_id}
