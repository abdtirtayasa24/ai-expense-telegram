from fastapi import FastAPI

from app.api.routes import auth, budgets, dashboard, health, transactions
from app.bot.webhook import router as telegram_webhook_router

app = FastAPI(
    title="AI Telegram Expense Tracker",
    version="0.1.0",
)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(budgets.router, prefix="/budgets", tags=["budgets"])
app.include_router(telegram_webhook_router, prefix="/webhooks", tags=["telegram"])
