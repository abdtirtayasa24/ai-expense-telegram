# MVP Milestone Implemented

## Milestone 0 — Repository and Tooling

Goal: Prepare monorepo for human and AI agentic coding.

### Finished Tasks

- Create monorepo structure.
- Add backend FastAPI app skeleton.
- Add frontend Vite React app.
- Add Supabase migrations folder (already finished by human).
- Add `.env.example` files (already finished by human).
- Add README with local setup.
- Add lint/test scripts.

### Delivered

- Running backend health endpoint.
- Running frontend placeholder page.
- Empty migrations committed.

### Acceptance Criteria

- `GET /health` returns `{ "status": "ok" }`.
- `npm run dev` starts frontend.
- `uvicorn app.main:app --reload` starts backend.
- README explains local setup.

---

## Milestone 1 — Database and Repository Layer

Goal: Build database foundation.

### Finished Tasks

- Implement Supabase migrations.
- Implement Supabase client.
- Implement repository classes:
  - `users_repository.py`
  - `transactions_repository.py`
  - `budgets_repository.py`
  - `insights_repository.py`
  - `conversation_states_repository.py`
- Add repository tests where practical.

### Delivered

- Tables created in Supabase.
- Backend can create, fetch, update users.
- Backend can create, fetch, update, delete transactions.

### Acceptance Criteria

- Migrations run successfully.
- `users.telegram_user_id` is unique.
- Foreign keys enforce user ownership.
- Indexes exist for common queries.

---

## Milestone 2 — Telegram Webhook and Admin Commands

Goal: Build private allowlist access.

### Finished Tasks

- Create Telegram bot with BotFather.
- Configure webhook route.
- Implement Telegram client.
- Implement admin command parser.
- Implement:
  - `/register <telegram_id>`
  - `/unreg <telegram_id>`
  - `/users`
- Implement admin-only validation using `ADMIN_TELEGRAM_ID`.

### Delivered

- Admin can manage users from Telegram.
- Non-admin users are blocked from admin commands.

### Acceptance Criteria

- `/register 123` creates active pending user.
- `/unreg 123` sets user inactive.
- `/users` lists all users.
- Non-admin receives access denied.
- Admin cannot unregister self.

---

## Milestone 3 — User Authorization and Onboarding

Goal: Ensure only registered users can use the app.

### Finished Tasks

- Implement user lookup by Telegram ID.
- Reject missing/inactive users.
- Implement onboarding state machine.
- Store first and last name.
- Block transaction parsing until onboarding completed.

### Delivered

- First-time registered user onboarding flow.
- Completed users can proceed to normal app usage.

### Acceptance Criteria

- Registered pending user is asked first name.
- First name and last name are saved.
- `onboarding_status` becomes `completed`.
- Unregistered users receive rejection message.
- Inactive users receive rejection message.

---

## Milestone 4 — Rule-Based Transaction Parser

Goal: Support cheap deterministic parsing for common Indonesian messages.

### Finished Tasks

- Implement text normalization.
- Implement amount parser.
- Implement type detector.
- Implement category detector.
- Implement date detector.
- Implement confidence scoring.
- Add unit tests.

### Delivered

- Rule parser returns `ParsedTransaction`.
- Common transaction messages are parsed without Gemini.

### Acceptance Criteria

- `Bayar parkir 5000` parses as expense, transportasi, 5000.
- `Beli kopi 18rb` parses as expense, makanan_minuman, 18000.
- `Gaji masuk 8000000` parses as income, pendapatan, 8000000.
- Simple valid messages reach confidence >= 0.75.

---

## Milestone 5 — Transaction Creation from Bot

Goal: Save parsed chat messages as transactions.

### Finished Tasks

- Connect webhook to parser.
- Insert parsed transactions.
- Send confirmation message.
- Ask clarification when parsing fails.
- Add transaction formatting utilities.

### Delivered

- User can record transactions by chatting.

### Acceptance Criteria

- User sends `Bayar parkir 5000`.
- Bot replies confirmation in Indonesian.
- Transaction appears in Supabase.
- Raw message is saved.
- Parser source is saved.

---

## Milestone 6 — Gemini Fallback Parser

Goal: Improve parsing of ambiguous natural-language messages.

### Finished Tasks

- Implement Gemini client.
- Configure structured JSON output.
- Implement strict Pydantic validation.
- Use Gemini only when rule parser confidence is below threshold.
- Add fallback tests with mocked Gemini responses.

### Delivered

- Ambiguous Indonesian messages can be parsed.
- Invalid Gemini output is rejected safely.

### Acceptance Criteria

- Low-confidence rule parse triggers Gemini.
- Gemini response passes schema validation before saving.
- Low Gemini confidence asks clarification.
- Gemini is not called for simple high-confidence messages.

---

## Milestone 7 — Mini App Authentication

Goal: Securely authenticate Telegram Mini App users.

### Finished Tasks

- Implement `/auth/telegram-mini-app`.
- Validate Telegram `initData`.
- Check active + onboarded user.
- Issue JWT.
- Add frontend auth bootstrap.
- Add access denied handling.

### Delivered

- Mini App can authenticate active users.
- Unauthorized users are blocked.

### Acceptance Criteria

- Valid active onboarded user receives JWT.
- Invalid initData returns 401/403.
- Inactive user returns 403.
- Pending onboarding user returns 403 with onboarding message.
- Frontend stores JWT for session.

---

## Milestone 8 — Transaction CRUD API and UI

Goal: Manage transactions from Mini App.

### Finished Tasks

- Implement transaction API endpoints.
- Implement frontend transaction list.
- Implement mobile-first compact transaction rows.
- Implement manual transaction form.
- Implement edit/delete.
- Enforce user ownership.

### Delivered

- User can manage transactions from dashboard with compact mobile-friendly rows and right-side actions.

### Acceptance Criteria

- User can list own transactions with pagination.
- User can create manual transaction.
- User can edit transaction.
- User can delete transaction.
- User cannot access another user's transaction.

---

## Milestone 9 — Dashboard API and UI

Goal: Show financial summary.

### Finished Tasks

- Implement summary aggregation.
- Implement category aggregation.
- Implement monthly trend aggregation.
- Implement recent transactions endpoint.
- Build dashboard components.
- Add mobile-first summary layout, interactive category donut, and compact trend bars.

### Delivered

- Mini App dashboard shows user's financial overview with mobile-first summary, category, trend, and recent transaction sections.

### Acceptance Criteria

- Dashboard shows monthly income.
- Dashboard shows monthly expenses.
- Dashboard shows net cashflow.
- Dashboard shows category breakdown as an interactive donut chart.
- Dashboard shows monthly trend as compact horizontal bars.
- Dashboard shows recent transactions.

---

## Milestone 10 — Budgets

Goal: Add monthly budget tracking.

### Finished Tasks

- Implement budget CRUD APIs.
- Implement budget UI.
- Calculate actual expense per category.
- Show remaining budget and percentage used.

### Delivered

- User can set and monitor category budgets.

### Acceptance Criteria

- User can create budget for category/month.
- User can edit budget.
- User can delete budget.
- Dashboard shows budget progress.
- Over-budget category is clearly identified.

---

## Milestone 11 — Advisor Service

Goal: Provide budgeting and cashflow advice.

### Finished Tasks

- Implement financial data aggregation.
- Implement advisor prompt.
- Implement advisor guardrails.
- Implement `/advisor/insights`.
- Implement `/advisor/chat`.
- Implement Insights page.
- Add tests for restricted advice.

### Delivered

- User gets Indonesian cashflow insights based on own data.

### Acceptance Criteria

- Advisor identifies overspending categories.
- Advisor explains monthly cashflow.
- Advisor gives savings suggestions based on surplus.
- Advisor can estimate debt payoff from surplus.
- Advisor refuses or redirects investment/product advice.

---

## Milestone 12 — Deployment and Production Readiness

Goal: Deploy MVP.

### Finished Tasks

- Build backend Dockerfile.
- Deploy backend to HTTPS host.
- Deploy frontend to Vercel/Netlify.
- Configure Telegram webhook.
- Configure Mini App URL button.
- Set production environment variables.
- Run smoke tests.

### Delivered

- Production MVP usable from Telegram.

### Acceptance Criteria

- Telegram bot webhook receives messages.
- Admin can register user.
- Registered user can onboard.
- User can record transactions.
- User can open Mini App dashboard.
- User can view dashboard and manage data.
- Advisor works.
- Secrets are not exposed in frontend.

---