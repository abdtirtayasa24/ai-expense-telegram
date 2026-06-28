"""Advisor service for budgeting/cashflow insights using Gemini."""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from google import genai
from google.genai import types

from app.repositories.base import Row
from app.repositories.budgets_repository import BudgetsRepository
from app.repositories.transactions_repository import TransactionsRepository

JAKARTA_TZ = ZoneInfo("Asia/Jakarta")

_SYSTEM_INSTRUCTION = (
    "You are an Indonesian-language personal budgeting and cashflow assistant. "
    "Your role is to help the user understand and improve their personal "
    "finances using only the historical transaction data provided by the "
    "system. "
    "You must answer in Indonesian. "
    "Core responsibilities: "
    "Analyze cashflow based on historical income and expense data. "
    "Identify budgeting patterns and spending habits. "
    "Summarize spending by category. "
    "Highlight unusually high or recurring expenses. "
    "Suggest practical ways to reduce expenses based on the user's own "
    "transaction history. "
    "Help the user set realistic savings targets based on observed income, "
    "expenses, and surplus cashflow. "
    "Provide simple debt payoff estimates based only on available surplus "
    "cashflow. "
    "Data-grounding rules: "
    "Only use transaction data, balances, budgets, debts, goals, or user "
    "profile information explicitly provided by the system or user. "
    "Do not invent income, expenses, debts, balances, interest rates, "
    "savings goals, or financial behavior. "
    "Do not make recommendations that are not supported by the user's "
    "available data. "
    "If the data is incomplete, unclear, inconsistent, or too limited, say "
    "so clearly. "
    "If there is not enough data to provide a reliable analysis, tell the "
    "user that the data is not sufficient yet and suggest that they record "
    "transactions more regularly. "
    "When making estimates, clearly state that they are simple projections "
    "based on the available historical data, not guarantees. "
    "Allowed topics: "
    "Cashflow analysis. Budgeting. Spending categories. Spending habits. "
    "Expense reduction based on user data. Savings targets. Simple debt "
    "payoff projections based on surplus cashflow. "
    "Prohibited topics: "
    "Do not recommend specific stocks, crypto assets, mutual funds, bonds, "
    "insurance products, loans, credit cards, financial apps, banks, "
    "brokers, or any other financial products. "
    "Do not provide tax advice. Do not provide legal advice. "
    "Do not guarantee financial outcomes. "
    "Do not promise that the user will reach a goal by a certain date "
    "unless it is clearly presented as a non-guaranteed projection based on "
    "current data. "
    "Do not give investment allocation advice or portfolio recommendations. "
    "Do not suggest taking new debt, refinancing, or applying for loans. "
    "Do not provide advice that depends on information not available in the "
    "user's transaction data. "
    "Response style: "
    "Use concise, practical, and easy-to-understand Indonesian. "
    "Be supportive, realistic, and non-judgmental. "
    "Avoid technical finance jargon unless necessary. "
    "Do not over-explain. Prefer clear action steps based on the user's data. "
    "If numbers are available, include simple calculations. "
    "Use IDR for all monetary values. "
    "Use the Asia/Jakarta timezone when discussing dates or periods. "
    "When relevant, include this disclaimer: "
    "\"Ini hanya estimasi berdasarkan data transaksi yang kamu catat, "
    "bukan nasihat keuangan profesional.\""
)

_INSIGHTS_INSTRUCTION = (
    "You are generating a monthly financial insight report. "
    "You will receive a JSON object containing the user's financial summary "
    "for the current month. "
    "Respond with a JSON object containing exactly three fields: "
    "\"summary\" (a concise paragraph in Indonesian analyzing the month), "
    "\"recommendations\" (a list of practical action items in Indonesian), "
    "and \"warnings\" (a list of issues or overspending alerts in "
    "Indonesian — return an empty list if there are none). "
    "If the data shows zero income and zero expenses, the summary should "
    "note that there is not enough data yet."
)


def _current_month_date() -> tuple[str, datetime]:
    now = datetime.now(JAKARTA_TZ)
    return now.strftime("%Y-%m"), now


def _month_start(year: int, month: int) -> datetime:
    return datetime(year, month, 1, tzinfo=JAKARTA_TZ)


def _row_amount(row: Row) -> Decimal:
    return Decimal(str(row["amount"]))


def _add_months(dt: datetime, delta: int) -> datetime:
    month_index = dt.year * 12 + (dt.month - 1) + delta
    return datetime(month_index // 12, (month_index % 12) + 1, 1, tzinfo=JAKARTA_TZ)


def build_advisor_context(
    user_id: str,
    transactions_repository: TransactionsRepository,
    budgets_repository: BudgetsRepository,
) -> dict[str, Any]:
    """Aggregate the current user's financial context for the current month."""
    period_key, now = _current_month_date()
    month_start = _month_start(now.year, now.month)
    next_start = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)  # type: ignore[attr-defined]

    income_total = Decimal("0")
    expense_total = Decimal("0")
    category_expenses: dict[str, Decimal] = {}
    recurring_names: dict[str, int] = {}

    rows = _list_all(
        transactions_repository, user_id, month_start.date(), next_start.date()
    )
    for row in rows:
        amount = _row_amount(row)
        category = str(row["category"])
        name = str(row["name"])
        if row.get("type") == "income":
            income_total += amount
        elif row.get("type") == "expense":
            expense_total += amount
            category_expenses[category] = (
                category_expenses.get(category, Decimal("0")) + amount
            )

    # Recurring detection: same name in previous months
    for delta in (1, 2):
        prev_start = _add_months(month_start, -delta)
        prev_next = _add_months(prev_start, 1)
        prev_rows = _list_all(
            transactions_repository,
            user_id,
            prev_start.date(),
            prev_next.date(),
        )
        for row in prev_rows:
            pname = str(row["name"])
            recurring_names[pname] = recurring_names.get(pname, 0) + 1

    current_names = {str(r["name"]) for r in rows}
    recurring = []
    seen: set[str] = set()
    for name, count in recurring_names.items():
        if count >= 2 and name in current_names and name not in seen:
            seen.add(name)
            match = next(r for r in rows if str(r["name"]) == name)
            recurring.append(
                {"name": name, "amount": float(_row_amount(match))}
            )

    net_cashflow = income_total - expense_total
    savings_rate = float(
        (net_cashflow / income_total * Decimal("100")).quantize(Decimal("0.01"))
    ) if income_total > 0 else 0.0

    top_categories = sorted(
        category_expenses.items(), key=lambda x: x[1], reverse=True
    )

    # Budget violations
    budgets = budgets_repository.list_for_user_month(user_id, month_start.date())
    violations = []
    for budget in budgets:
        cat = str(budget["category"])
        limit = Decimal(str(budget["monthly_limit"]))
        actual = category_expenses.get(cat, Decimal("0"))
        if actual > limit:
            violations.append(
                {"category": cat, "budget": float(limit), "actual": float(actual)}
            )

    # Last 3 months trend
    trend = []
    for delta in range(2, -1, -1):
        m_start = _add_months(month_start, -delta)
        m_next = _add_months(m_start, 1)
        m_rows = _list_all(
            transactions_repository, user_id, m_start.date(), m_next.date()
        )
        m_income = Decimal("0")
        m_expense = Decimal("0")
        for row in m_rows:
            amt = _row_amount(row)
            if row.get("type") == "income":
                m_income += amt
            elif row.get("type") == "expense":
                m_expense += amt
        trend.append(
            {
                "month": m_start.strftime("%Y-%m"),
                "income_total": float(m_income),
                "expense_total": float(m_expense),
                "net_cashflow": float(m_income - m_expense),
            }
        )

    return {
        "period": period_key,
        "income_total": float(income_total),
        "expense_total": float(expense_total),
        "net_cashflow": float(net_cashflow),
        "savings_rate_percent": savings_rate,
        "top_categories": [
            {"category": cat, "amount": float(amt)}
            for cat, amt in top_categories[:5]
        ],
        "budget_violations": violations,
        "recurring_expenses": recurring[:5],
        "last_3_months": trend,
    }


def _list_all(
    repository: TransactionsRepository,
    user_id: str,
    month_start: Any,
    next_month_start: Any,
) -> list[Row]:
    """Fetch all expense+income transactions for a month range."""
    rows: list[Row] = []
    offset = 0
    page_size = 1000
    while True:
        page = repository.list_for_user(  # type: ignore[call-arg]
            user_id,
            month_start=month_start,
            next_month_start=next_month_start,
            limit=page_size,
            offset=offset,
        )
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += page_size


async def generate_insights(
    context: dict[str, Any],
    api_key: str,
    model: str,
) -> dict[str, Any]:
    """Call Gemini to generate a monthly insights report."""
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "recommendations": {"type": "array", "items": {"type": "string"}},
                "warnings": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["summary", "recommendations", "warnings"],
        },
        system_instruction=_INSIGHTS_INSTRUCTION,
    )
    prompt = (
        f"Today date: {context['period']}\n"
        f"Timezone: Asia/Jakarta\n\n"
        f"User financial context:\n{json.dumps(context, ensure_ascii=False)}\n\n"
        f"Generate a monthly financial insight report in Indonesian."
    )
    response = await client.aio.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )
    if response.parsed is None:
        raise ValueError("Gemini did not return structured insights output.")
    return response.parsed


async def generate_chat_answer(
    context: dict[str, Any],
    message: str,
    api_key: str,
    model: str,
    chat_history: list[Row] | None = None,
) -> str:
    """Call Gemini to answer an advisor chat question."""
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=_SYSTEM_INSTRUCTION,
    )
    history = chat_history or []
    prompt = (
        f"Today date: {context['period']}\n"
        f"Timezone: Asia/Jakarta\n\n"
        f"User financial context:\n{json.dumps(context, ensure_ascii=False)}\n\n"
        f"Recent advisor conversation:\n"
        f"{json.dumps(_format_chat_history(history), ensure_ascii=False)}\n\n"
        f"User question:\n{message}\n\n"
        f"Answer in Indonesian using only the data provided above. "
        f"Use recent conversation only for continuity; do not invent financial data."
    )
    response = await client.aio.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )
    return response.text or "Maaf, saya belum bisa menjawab pertanyaan ini."


def _format_chat_history(history: list[Row]) -> list[dict[str, str]]:
    return [
        {
            "role": str(row.get("role", "")),
            "content": str(row.get("content", "")),
        }
        for row in history
        if row.get("role") in {"user", "assistant"} and row.get("content")
    ]
