from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.parser import TransactionCategory

TransactionType = Literal["income", "expense"]
TransactionSource = Literal["telegram_chat", "manual"]
TransactionParser = Literal["rule_based", "gemini", "manual"]


class TransactionBase(BaseModel):
    type: TransactionType
    name: str = Field(min_length=1, max_length=120)
    category: TransactionCategory
    amount: Decimal = Field(gt=0)
    transaction_date: date
    note: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("name is required")
        return name

    @field_validator("note")
    @classmethod
    def strip_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        note = value.strip()
        return note or None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    type: TransactionType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: TransactionCategory | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    transaction_date: date | None = None
    note: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        name = value.strip()
        if not name:
            raise ValueError("name is required")
        return name

    @field_validator("note")
    @classmethod
    def strip_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        note = value.strip()
        return note or None


class TransactionOut(BaseModel):
    id: str
    type: TransactionType
    name: str
    category: TransactionCategory
    amount: float
    transaction_date: date
    note: str | None = None
    source: TransactionSource
    parser: TransactionParser
    confidence_score: float | None = None


class TransactionListResponse(BaseModel):
    items: list[TransactionOut]
    limit: int
    offset: int


class TransactionDeleteResponse(BaseModel):
    deleted: bool
