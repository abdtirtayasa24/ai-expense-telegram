from pydantic import BaseModel


class InsightsResponse(BaseModel):
    summary: str
    recommendations: list[str]
    warnings: list[str]


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
