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

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed application architecture, especially:

- [Core Flows](docs/ARCHITECTURE.md#core-flows)
- [API Surface](docs/ARCHITECTURE.md#api-surface)
- [Code Architecture](docs/ARCHITECTURE.md#code-architecture)
- [Data Model](docs/ARCHITECTURE.md#data-model)

## Project Structure

```text
ai-expense-telegram/
  backend/
    app/
      api/routes/       # auth, transactions, budgets, dashboard, advisor, settings, internal jobs
      bot/              # Telegram webhook, commands, onboarding, advisor mode, responses
      core/             # config, telegram_auth
      integrations/     # supabase_client, telegram_client
      repositories/     # users, transactions, budgets, insights, conversation_states, advisor_chat
      schemas/          # auth, transaction, budget, dashboard, advisor, parser
      services/         # parser, advisor, cashflow period, timeout, categories, jwt services
      main.py
    tests/              # backend tests
    .env.example
    Dockerfile
    pyproject.toml
  docs/
    ARCHITECTURE.md
    DEPLOYMENT.md
    MVP_IMPLEMENTED.md
  frontend/
    src/
      api/              # auth, transactions, budgets, dashboard, advisor, settings
      assets/           # app logo
      components/       # dashboard, page navigation, budget, advisor, settings, transaction panels/modals
      utils/            # helper functions
      App.tsx
      main.tsx
      styles.css
      vite-env.d.ts
    .env.example
    eslint.config.js
    global.d.ts
    index.html
    package.json
    tsconfig.json
    vite.config.ts
  scripts/              # smoke_test.py
  supabase/migrations/  # sql migrations
  .gitignore
  AGENTS.md
  README.md
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

Migrations are in `supabase/migrations/`. For MVP, the maintainer applies these manually via Supabase SQL editor. Run all migrations in numeric order, currently 001 through 010.

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full deployment instructions.

## License

Private project. Not licensed for redistribution.
