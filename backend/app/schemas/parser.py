from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

TransactionCategory = Literal[
    "transportasi",
    "makanan_minuman",
    "tagihan",
    "tempat_tinggal",
    "belanja",
    "hiburan",
    "utang_cicilan",
    "pendapatan",
    "kesehatan",
    "pendidikan",
    "keluarga",
    "lainnya",
]
TransactionType = Literal["income", "expense"]
ParserType = Literal["rule_based", "gemini", "manual"]


class ParsedTransaction(BaseModel):
    name: str
    amount: Decimal | None
    type: TransactionType | None
    category: TransactionCategory
    transaction_date: date
    parser: ParserType
    confidence_score: float = Field(ge=0, le=1)
    needs_clarification: bool
    clarification_question: str | None = None
