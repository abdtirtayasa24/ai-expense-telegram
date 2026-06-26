# AI Telegram Expense Tracker

Private Indonesian-only expense tracker and budgeting advisor for Telegram Bot + Telegram Mini App.

## Local development

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
```

Expected response:

```json
{ "status": "ok" }
```

Useful checks:

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

Useful checks:

```bash
cd frontend
npm run typecheck
npm run lint
npm run build
```

## Environment

Use the `.env.example` files as templates. Keep real secrets out of git.

- Backend secrets such as `TELEGRAM_BOT_TOKEN`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, and `JWT_SECRET_KEY` must stay server-side only.
- Frontend configuration must use safe `VITE_` variables only.
- The Gemini model value currently used by code/env is the source of truth.

## Supabase migrations

Supabase migrations are stored in `supabase/migrations/`. For MVP development, the maintainer applies these migrations manually through Supabase SQL editor or another approved Supabase workflow.
