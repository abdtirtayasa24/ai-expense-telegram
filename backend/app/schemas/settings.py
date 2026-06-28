from pydantic import BaseModel, Field


class UserSettingsOut(BaseModel):
    cashflow_period_start_day: int


class CashflowPeriodUpdate(BaseModel):
    cashflow_period_start_day: int = Field(ge=1, le=31)
