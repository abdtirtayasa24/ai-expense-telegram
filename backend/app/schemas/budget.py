from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.parser import TransactionCategory


class BudgetCreate(BaseModel):
    category: TransactionCategory
    monthly_limit: Decimal = Field(gt=0)
    month: date | None = None


class BudgetUpdate(BaseModel):
    monthly_limit: Decimal | None = Field(default=None, gt=0)


class BudgetOut(BaseModel):
    id: str
    category: TransactionCategory
    monthly_limit: float
    month: date
    actual: float
    remaining: float
    percent_used: float


class BudgetListResponse(BaseModel):
    items: list[BudgetOut]


class BudgetDeleteResponse(BaseModel):
    deleted: bool
