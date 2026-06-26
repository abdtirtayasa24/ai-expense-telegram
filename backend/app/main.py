from fastapi import FastAPI

from app.api.routes import health

app = FastAPI(
    title="AI Telegram Expense Tracker",
    version="0.1.0",
)

app.include_router(health.router, prefix="/health", tags=["health"])
