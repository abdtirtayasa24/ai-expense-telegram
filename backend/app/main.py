from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import advisor, auth, budgets, dashboard, health, transactions
from app.bot.webhook import router as telegram_webhook_router
from app.core.config import settings

app = FastAPI(
    title="AI Telegram Expense Tracker",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.mini_app_url,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(budgets.router, prefix="/budgets", tags=["budgets"])
app.include_router(advisor.router, prefix="/advisor", tags=["advisor"])
app.include_router(telegram_webhook_router, prefix="/webhooks", tags=["telegram"])
