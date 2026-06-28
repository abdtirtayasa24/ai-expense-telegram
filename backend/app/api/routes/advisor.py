from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_advisor_chat_repository,
    get_budgets_repository,
    get_current_user,
    get_settings,
    get_transactions_repository,
)
from app.repositories.advisor_chat_repository import AdvisorChatRepository
from app.repositories.base import Row
from app.repositories.budgets_repository import BudgetsRepository
from app.repositories.insights_repository import InsightsRepository
from app.repositories.transactions_repository import TransactionsRepository
from app.schemas.advisor import ChatRequest, ChatResponse, InsightsResponse
from app.services.advisor_chat_service import answer_advisor_question
from app.services.advisor_service import (
    build_advisor_context,
    generate_insights,
)

router = APIRouter()


@router.post("/insights", response_model=InsightsResponse)
async def advisor_insights(
    current_user: Annotated[Row, Depends(get_current_user)],
    settings: Annotated[Any, Depends(get_settings)],
    transactions_repository: Annotated[
        TransactionsRepository,
        Depends(get_transactions_repository),
    ],
    budgets_repository: Annotated[
        BudgetsRepository,
        Depends(get_budgets_repository),
    ],
) -> InsightsResponse:
    context = build_advisor_context(
        current_user["id"],
        transactions_repository,
        budgets_repository,
    )
    try:
        result = await generate_insights(
            context,
            settings.gemini_api_key,
            settings.gemini_model,
        )
    except Exception:
        return InsightsResponse(
            summary="Maaf, insight belum bisa dibuat saat ini. Coba lagi nanti.",
            recommendations=[],
            warnings=[],
        )

    insights_repo = InsightsRepository()
    insights_repo.create(
        user_id=current_user["id"],
        period_start=context["last_3_months"][0]["month"] + "-01",
        period_end=context["period"] + "-01",
        insight_type="monthly_insights",
        summary=result["summary"],
    )
    return InsightsResponse(
        summary=result["summary"],
        recommendations=result.get("recommendations", []),
        warnings=result.get("warnings", []),
    )


@router.post("/chat", response_model=ChatResponse)
async def advisor_chat(
    payload: ChatRequest,
    current_user: Annotated[Row, Depends(get_current_user)],
    settings: Annotated[Any, Depends(get_settings)],
    transactions_repository: Annotated[
        TransactionsRepository,
        Depends(get_transactions_repository),
    ],
    budgets_repository: Annotated[
        BudgetsRepository,
        Depends(get_budgets_repository),
    ],
    advisor_chat_repository: Annotated[
        AdvisorChatRepository,
        Depends(get_advisor_chat_repository),
    ],
) -> ChatResponse:
    try:
        answer = await answer_advisor_question(
            user_id=current_user["id"],
            message=payload.message,
            source="mini_app",
            transactions_repository=transactions_repository,
            budgets_repository=budgets_repository,
            advisor_chat_repository=advisor_chat_repository,
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            history_limit=settings.advisor_chat_history_limit,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Layanan advisor sedang tidak tersedia. Coba lagi nanti.",
        )
    return ChatResponse(answer=answer)
