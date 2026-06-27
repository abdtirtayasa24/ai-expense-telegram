from pydantic import BaseModel

from app.schemas.transaction import TransactionOut


class DashboardSummary(BaseModel):
    month: str
    income_total: float
    expense_total: float
    net_cashflow: float
    savings_rate_percent: float


class CategoryBreakdownItem(BaseModel):
    category: str
    amount: float
    percent: float


class CategoryBreakdownResponse(BaseModel):
    items: list[CategoryBreakdownItem]


class TrendItem(BaseModel):
    month: str
    income_total: float
    expense_total: float
    net_cashflow: float


class TrendResponse(BaseModel):
    items: list[TrendItem]


class RecentTransactionsResponse(BaseModel):
    items: list[TransactionOut]
