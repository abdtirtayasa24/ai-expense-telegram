import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from google import genai
from google.genai import types

from app.prompts.loader import load_prompt
from app.repositories.base import Row
from app.repositories.budgets_repository import BudgetsRepository
from app.repositories.transactions_repository import TransactionsRepository
from app.services.cashflow_period import (
    add_months,
    current_cashflow_period,
    period_start_for_month,
    today_jakarta,
)

JAKARTA_TZ = ZoneInfo("Asia/Jakarta")

FIXED_OR_MONTHLY_EXPENSE_CATEGORIES = {
    "tagihan",
    "tempat_tinggal",
    "utang_cicilan",
}
DAILY_OR_VARIABLE_EXPENSE_CATEGORIES = {
    "transportasi",
    "makanan_minuman",
    "belanja",
    "hiburan",
    "kesehatan",
    "pendidikan",
    "keluarga",
}

_SYSTEM_INSTRUCTION = load_prompt("advisor_chat.md")
_INSIGHTS_INSTRUCTION = load_prompt("advisor_insights.md")


def advisor_context_hash(context: dict[str, Any]) -> str:
    payload = json.dumps(
        context,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _period_key(period_start: datetime, start_day: int) -> str:
    if start_day == 1:
        return period_start.strftime("%Y-%m")
    return period_start.date().isoformat()


def _row_amount(row: Row) -> Decimal:
    return Decimal(str(row["amount"]))


def build_advisor_context(
    user_id: str,
    transactions_repository: TransactionsRepository,
    budgets_repository: BudgetsRepository,
    cashflow_period_start_day: int = 1,
) -> dict[str, Any]:
    period_start_date, next_start_date = current_cashflow_period(
        cashflow_period_start_day,
    )
    period_key = (
        period_start_date.strftime("%Y-%m")
        if cashflow_period_start_day == 1
        else period_start_date.isoformat()
    )
    month_start = datetime.combine(period_start_date, datetime.min.time(), JAKARTA_TZ)
    next_start = datetime.combine(next_start_date, datetime.min.time(), JAKARTA_TZ)

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

    for delta in (1, 2):
        prev_start_date = period_start_for_month(
            add_months(period_start_date.replace(day=1), -delta),
            cashflow_period_start_day,
        )
        prev_next_date = period_start_for_month(
            add_months(period_start_date.replace(day=1), -(delta - 1)),
            cashflow_period_start_day,
        )
        prev_start = datetime.combine(prev_start_date, datetime.min.time(), JAKARTA_TZ)
        prev_next = datetime.combine(prev_next_date, datetime.min.time(), JAKARTA_TZ)
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
    surplus_rate = _percentage(net_cashflow, income_total)
    period_progress = _period_progress(period_start_date, next_start_date)

    top_categories = sorted(
        category_expenses.items(), key=lambda x: x[1], reverse=True
    )

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

    trend = []
    for delta in range(2, -1, -1):
        m_start_date = period_start_for_month(
            add_months(period_start_date.replace(day=1), -delta),
            cashflow_period_start_day,
        )
        m_next_date = period_start_for_month(
            add_months(period_start_date.replace(day=1), -(delta - 1)),
            cashflow_period_start_day,
        )
        m_start = datetime.combine(m_start_date, datetime.min.time(), JAKARTA_TZ)
        m_next = datetime.combine(m_next_date, datetime.min.time(), JAKARTA_TZ)
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
                "month": _period_key(m_start, cashflow_period_start_day),
                "income_total": float(m_income),
                "expense_total": float(m_expense),
                "net_cashflow": float(m_income - m_expense),
            }
        )

    cadence_breakdown = _expense_cadence_breakdown(rows)
    variable_expense_total = _cadence_total(
        cadence_breakdown["likely_daily_or_variable"]
    )
    fixed_expense_total = _cadence_total(
        cadence_breakdown["likely_monthly_or_fixed"]
    )
    unclear_expense_total = _cadence_total(cadence_breakdown["unclear_or_one_off"])
    elapsed_days = period_progress["period_elapsed_days"]
    total_days = period_progress["period_total_days"]
    average_daily_expense = _safe_divide(expense_total, elapsed_days)
    average_daily_variable_expense = _safe_divide(variable_expense_total, elapsed_days)
    projected_expense_total = (
        fixed_expense_total
        + unclear_expense_total
        + average_daily_variable_expense * Decimal(total_days)
    )
    projected_net_cashflow = income_total - projected_expense_total

    return {
        "period": period_key,
        "period_start": period_start_date.isoformat(),
        "period_end": next_start_date.isoformat(),
        "income_total": float(income_total),
        "expense_total": float(expense_total),
        "net_cashflow": float(net_cashflow),
        "surplus_rate_percent": surplus_rate,
        **period_progress,
        "average_daily_expense_so_far": _money_float(average_daily_expense),
        "average_daily_variable_expense_so_far": _money_float(
            average_daily_variable_expense
        ),
        "projected_expense_total_at_current_pace": _money_float(
            projected_expense_total
        ),
        "projected_net_cashflow_at_current_pace": _money_float(
            projected_net_cashflow
        ),
        "projected_surplus_rate_percent": _percentage(
            projected_net_cashflow, income_total
        ),
        "top_categories": [
            {"category": cat, "amount": float(amt)}
            for cat, amt in top_categories[:5]
        ],
        "budget_violations": violations,
        "recurring_expenses": recurring[:5],
        "expense_cadence_breakdown": cadence_breakdown,
        "last_3_months": trend,
    }


def _money_float(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


def _percentage(numerator: Decimal, denominator: Decimal) -> float:
    if denominator <= 0:
        return 0.0
    value = numerator / denominator * Decimal("100")
    return float(value.quantize(Decimal("0.01")))


def _safe_divide(value: Decimal, divisor: int) -> Decimal:
    if divisor <= 0:
        return Decimal("0")
    return value / Decimal(divisor)


def _period_progress(period_start: date, period_end: date) -> dict[str, int | float]:
    today = today_jakarta()
    total_days = max((period_end - period_start).days, 1)
    if today < period_start:
        elapsed_days = 0
    elif today >= period_end:
        elapsed_days = total_days
    else:
        elapsed_days = (today - period_start).days + 1
    remaining_days = max(total_days - elapsed_days, 0)
    progress = Decimal(elapsed_days) / Decimal(total_days) * Decimal("100")
    return {
        "period_elapsed_days": elapsed_days,
        "period_total_days": total_days,
        "period_remaining_days": remaining_days,
        "period_progress_percent": float(progress.quantize(Decimal("0.01"))),
    }


def _expense_cadence_breakdown(rows: list[Row]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, dict[str, Decimal | int]] = {}
    for row in rows:
        if row.get("type") != "expense":
            continue
        category = str(row["category"])
        current = grouped.setdefault(
            category,
            {"amount": Decimal("0"), "transaction_count": 0},
        )
        current["amount"] = Decimal(str(current["amount"])) + _row_amount(row)
        current["transaction_count"] = int(current["transaction_count"]) + 1

    breakdown = {
        "likely_monthly_or_fixed": [],
        "likely_daily_or_variable": [],
        "unclear_or_one_off": [],
    }
    for category, values in sorted(grouped.items()):
        amount = Decimal(str(values["amount"]))
        transaction_count = int(values["transaction_count"])
        item = {
            "category": category,
            "amount": float(amount),
            "transaction_count": transaction_count,
        }
        if category in FIXED_OR_MONTHLY_EXPENSE_CATEGORIES:
            breakdown["likely_monthly_or_fixed"].append(
                {**item, "reason": "kategori pengeluaran tetap/bulanan"}
            )
        elif category in DAILY_OR_VARIABLE_EXPENSE_CATEGORIES:
            breakdown["likely_daily_or_variable"].append(
                {**item, "reason": "kategori pengeluaran harian/variabel"}
            )
        else:
            breakdown["unclear_or_one_off"].append(
                {**item, "reason": "kategori belum cukup jelas untuk diproyeksikan"}
            )
    return breakdown


def _cadence_total(items: list[dict[str, Any]]) -> Decimal:
    total = Decimal("0")
    for item in items:
        total += Decimal(str(item["amount"]))
    return total


def _list_all(
    repository: TransactionsRepository,
    user_id: str,
    month_start: Any,
    next_month_start: Any,
) -> list[Row]:
    rows: list[Row] = []
    cursor_id: str | None = None
    page_size = 1000
    while True:
        page = repository.list_for_user_after_id(
            user_id,
            cursor_id=cursor_id,
            month_start=month_start,
            next_month_start=next_month_start,
            limit=page_size,
            columns="id,type,name,category,amount,transaction_date",
        )
        rows.extend(page)
        if len(page) < page_size:
            return rows
        cursor_id = str(page[-1]["id"])


async def generate_insights(
    context: dict[str, Any],
    api_key: str,
    model: str,
) -> dict[str, Any]:
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
        f"Today date: {today_jakarta().isoformat()}\n"
        f"Current period: {context['period']}\n"
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
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=_SYSTEM_INSTRUCTION,
    )
    history = chat_history or []
    prompt = (
        f"Today date: {today_jakarta().isoformat()}\n"
        f"Current period: {context['period']}\n"
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
