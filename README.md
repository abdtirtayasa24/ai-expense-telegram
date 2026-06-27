# AI Telegram Expense Tracker

Private Indonesian-only expense tracker and budgeting advisor for Telegram Bot + Telegram Mini App.

Users record expenses and income by chatting with a Telegram bot in Indonesian natural language. A React Telegram Mini App provides a full dashboard with monthly summaries, category breakdowns, trends, budget tracking, transaction management, and AI-powered budgeting advice.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python FastAPI |
| Database | Supabase PostgreSQL |
| Frontend | React + Vite (Telegram Mini App) |
| Bot | Telegram Bot API webhook |
| AI Parser (fallback) | Google Gemini structured output |
| AI Advisor | Google Gemini with guardrails |
| Auth | Telegram initData HMAC + JWT |
| Deployment | Docker (backend), Vercel/Netlify (frontend) |

## Implemented Milestones

- [x] Repository and tooling bootstrap (M0)
- [x] Database repository layer (M1)
- [x] Telegram webhook and admin commands (M2)
- [x] User authorization and onboarding (M3)
- [x] Rule-based transaction parser (M4)
- [x] Transaction creation from bot (M5)
- [x] Gemini fallback parser (M6)
- [x] Mini App authentication (M7)
- [x] Transaction CRUD API and UI (M8)
- [x] Dashboard API and UI (M9)
- [x] Budget CRUD API and UI (M10)
- [x] Advisor service and guardrails (M11)
- [ ] Production deployment (M12)

## Project Structure

```text
ai-expense-telegram/
  backend/
    app/
      api/routes/       # auth, transactions, budgets, dashboard, advisor
      bot/              # Telegram webhook, commands, onboarding, responses
      core/             # config, telegram_auth
      integrations/     # supabase_client, telegram_client
      repositories/     # users, transactions, budgets, insights, conversation_states
      schemas/          # auth, transaction, budget, dashboard, advisor, parser
      services/         # rule_parser, gemini_parser, advisor_service, transaction_categories, jwt_service
    tests/
    pyproject.toml
    Dockerfile
    .env.example
  frontend/
    src/
      api/              # auth, transactions, budgets, dashboard, advisor
      components/       # DashboardOverview, TransactionsPanel, BudgetPanel, InsightPanel
    package.json
    vite.config.ts
  supabase/migrations/  # 001–007
  scripts/              # smoke_test.py
  docs/
    SPEC-1-ai-telegram-expense-tracker.md
    DEPLOYMENT.md
```

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

Run tests and lint:

```bash
cd backend
python -m pytest
ruff check .
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Build and lint:

```bash
cd frontend
npm run build
npm run lint
```

## Environment Variables

Use `.env.example` files as templates. Keep real secrets out of git.

| Variable | Backend | Frontend | Notes |
|---|---|---|---|
| `APP_BASE_URL` | ✅ | | Public backend URL |
| `MINI_APP_URL` | ✅ | | Public frontend URL |
| `TELEGRAM_BOT_TOKEN` | ✅ | | From BotFather |
| `ADMIN_TELEGRAM_ID` | ✅ | | Numeric Telegram user ID |
| `SUPABASE_URL` | ✅ | | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | | **Server-side only** |
| `GEMINI_API_KEY` | ✅ | | **Server-side only** |
| `GEMINI_MODEL` | ✅ | | e.g. gemini-2.5-flash |
| `JWT_SECRET_KEY` | ✅ | | Long random string |
| `VITE_API_BASE_URL` | | ✅ | Backend URL for frontend |

## Supabase Migrations

Migrations are in `supabase/migrations/`. For MVP, the maintainer applies these manually via Supabase SQL editor. Run 001 through 007 in order.

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full deployment instructions.

## License

Private project. Not licensed for redistribution.
