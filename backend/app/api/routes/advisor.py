from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_advisor_chat_repository,
    get_budgets_repository,
    get_current_user,
    get_insights_repository,
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
    advisor_context_hash,
    build_advisor_context,
    generate_insights,
)
from app.services.cashflow_period import user_cashflow_start_day

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
    insights_repository: Annotated[
        InsightsRepository,
        Depends(get_insights_repository),
    ],
) -> InsightsResponse:
    context = build_advisor_context(
        current_user["id"],
        transactions_repository,
        budgets_repository,
        cashflow_period_start_day=user_cashflow_start_day(current_user),
    )
    period_start = date.fromisoformat(context["period_start"])
    period_end = date.fromisoformat(context["period_end"])
    context_hash = advisor_context_hash(context)
    cached = insights_repository.get_cached_for_context(
        user_id=current_user["id"],
        period_start=period_start,
        period_end=period_end,
        insight_type="monthly_insights",
        context_hash=context_hash,
    )
    if cached is not None and isinstance(cached.get("result"), dict):
        result = cached["result"]
        return InsightsResponse(
            summary=str(result.get("summary", cached["summary"])),
            recommendations=list(result.get("recommendations", [])),
            warnings=list(result.get("warnings", [])),
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

    insights_repository.create(
        user_id=current_user["id"],
        period_start=period_start,
        period_end=period_end,
        insight_type="monthly_insights",
        summary=result["summary"],
        result={
            "summary": result["summary"],
            "recommendations": result.get("recommendations", []),
            "warnings": result.get("warnings", []),
        },
        context_hash=context_hash,
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
            cashflow_period_start_day=user_cashflow_start_day(current_user),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Layanan advisor sedang tidak tersedia. Coba lagi nanti.",
        )
    return ChatResponse(answer=answer)
