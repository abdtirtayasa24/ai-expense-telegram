# Deployment Guide

## Prerequisites

- A Linux server or cloud VM (or any Docker-capable host) with **HTTPS** configured.
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather).
- A Supabase project with PostgreSQL.
- A Google Gemini API key.
- Python 3.12+ and Node.js 20+ (for building locally, optional if using Docker).
- `requests` Python package for smoke tests (`pip install requests`).

## 1. Supabase Migrations

Apply all SQL migrations from `supabase/migrations/` **manually** via the Supabase SQL editor:

1. Open your Supabase project → SQL Editor.
2. Run each migration file in order (001 through 007).

Verify tables exist: `users`, `transactions`, `budgets`, `advisor_insights`, `conversation_states`.

## 2. Backend Deployment

### Option A — Docker (Recommended)

```bash
cd backend

# Build
docker build -t ai-expense-telegram-backend .

# Run with environment variables
docker run -d \
  --name expense-backend \
  -p 8000:8000 \
  -e APP_BASE_URL=https://api.yourdomain.com \
  -e MINI_APP_URL=https://app.yourdomain.com \
  -e TELEGRAM_BOT_TOKEN=your_bot_token \
  -e ADMIN_TELEGRAM_ID=your_telegram_id \
  -e SUPABASE_URL=https://your-project.supabase.co \
  -e SUPABASE_SERVICE_ROLE_KEY=your_service_role_key \
  -e GEMINI_API_KEY=your_gemini_key \
  -e GEMINI_MODEL=gemini-2.5-flash \
  -e JWT_SECRET_KEY=your_long_random_secret \
  -e DEFAULT_LANGUAGE=id \
  -e DEFAULT_CURRENCY=IDR \
  -e DEFAULT_TIMEZONE=Asia/Jakarta \
  -e PARSER_CONFIDENCE_THRESHOLD=0.75 \
  ai-expense-telegram-backend
```

### Option B — Direct

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# Edit .env with production values
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Verify backend

```bash
curl https://api.yourdomain.com/health
# Expected: {"status":"ok"}
```

## 3. Frontend Deployment

### Option A — Vercel (Recommended)

1. Push the repository to GitHub.
2. Import the project in Vercel.
3. Set root directory to `frontend`.
4. Set build command: `npm run build`.
5. Set output directory: `dist`.
6. Add environment variable: `VITE_API_BASE_URL=https://api.yourdomain.com`.
7. Deploy.

### Option B — Netlify

1. Connect the repository.
2. Set base directory to `frontend`.
3. Set build command: `npm run build`.
4. Set publish directory: `frontend/dist`.
5. Add environment variable: `VITE_API_BASE_URL=https://api.yourdomain.com`.
6. Deploy.

### Option C — Docker with nginx

```bash
cd frontend
npm install
npm run build

# Serve dist/ with any static file server (nginx, serve, etc.)
npx serve dist -p 3000
```

### Verify frontend

Open the Mini App URL in Telegram or a browser. You should see the auth loading state.

## 4. Telegram Bot Configuration

### Set the webhook

```bash
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=https://api.yourdomain.com/webhooks/telegram"
```

Verify:

```bash
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
```

### Set Mini App button

1. Open BotFather.
2. Send `/mybots` → select your bot → Bot Settings → Menu Button.
3. Set the button text (e.g., "Buka Dashboard").
4. Set the button URL to your frontend URL (`https://app.yourdomain.com`).

## 5. Register Admin User

Send a message to your bot on Telegram:

```
/register <YOUR_ADMIN_TELEGRAM_ID>
```

Replace `<YOUR_ADMIN_TELEGRAM_ID>` with the numeric Telegram user ID matching `ADMIN_TELEGRAM_ID`.

## 6. Run Smoke Tests

```bash
pip install requests

TELEGRAM_BOT_TOKEN=your_bot_token \
  BASE_URL=https://api.yourdomain.com \
  python scripts/smoke_test.py
```

Expected output:

```
Smoke testing https://api.yourdomain.com

  ✅ GET /health
  ✅ POST /auth/telegram-mini-app
  ✅ GET /transactions
  ✅ GET /dashboard/summary
  ✅ GET /budgets
  ✅ POST /advisor/insights

6/6 passed
All smoke tests passed. 🚀
```

## 7. Full End-to-End Manual Walkthrough

After smoke tests pass, manually verify:

1. Admin registers a real user: `/register <telegram_id>`.
2. Registered user chats with the bot and completes onboarding (first name, last name).
3. User records expenses and income via chat: `Bayar parkir 5000`, `Gaji masuk 8000000`.
4. User opens the Mini App from the Telegram menu button.
5. Mini App authenticates and shows dashboard with real data.
6. User creates/edits/deletes transactions from the Mini App.
7. User creates/edits budgets and sees progress.
8. User generates advisor insights and chats with the advisor.
9. Verify another user cannot see the first user's data.

## 8. Secret Audit

- Verify `backend/.env` is **not** committed to git.
- Search frontend `dist/` for any keys: `grep -r "sk-" dist/`, `grep -r "eyJ" dist/`, `grep -r "supabase" dist/`.
- Verify no `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, or `JWT_SECRET_KEY` appear in frontend assets.
- Verify backend logs do not print raw tokens or API keys.

## Environment Variables Checklist

| Variable | Backend | Frontend |
|---|---|---|
| `APP_BASE_URL` | ✅ | |
| `MINI_APP_URL` | ✅ | |
| `TELEGRAM_BOT_TOKEN` | ✅ | |
| `ADMIN_TELEGRAM_ID` | ✅ | |
| `SUPABASE_URL` | ✅ | |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | |
| `GEMINI_API_KEY` | ✅ | |
| `GEMINI_MODEL` | ✅ | |
| `JWT_SECRET_KEY` | ✅ | |
| `VITE_API_BASE_URL` | | ✅ |
