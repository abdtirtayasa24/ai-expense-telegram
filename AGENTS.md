# AI Telegram Expense Tracker — Agent Guide

This document is the definitive guide for any AI coding agent (or human contributor) continuing development on this project. Before working and make any changes, read this AGENTS.md and:

- [README.md](README.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/MVP_IMPLEMENTED.md](docs/MVP_IMPLEMENTED.md)

## Project Identity

- **Name:** AI Telegram Expense Tracker
- **Purpose:** Private Indonesian-only personal finance tracker via Telegram Bot + Mini App
- **Language:** Indonesian (bot/advisors/UI), English (code/docs)
- **Currency:** IDR (whole numbers, no decimals)
- **Timezone:** Asia/Jakarta
- **Access Model:** Private allowlist (admin registers users via Telegram)

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | Python FastAPI |
| Async | `async def` for I/O, `def` for CPU-bound |
| ORM/Database | Supabase Python client (no ORM, raw queries via repository pattern) |
| Database | Supabase PostgreSQL |
| Auth | Telegram initData HMAC → JWT (python-jose) |
| AI / LLM | Google Gemini (`google-genai` SDK) |
| Frontend | React 19 + TypeScript + Vite |
| Styling | Plain CSS (no CSS framework) |
| Charts | CSS-only (no chart library used; recharts is installed but unused) |
| HTTP client (frontend) | Axios |
| Linting (backend) | Ruff (line length 88, target py311, rules E/F/I/UP) |
| Linting (frontend) | ESLint + typescript-eslint |
| Testing (backend) | pytest + pytest-asyncio |
| Deployment | Docker (backend), Vercel/Netlify (frontend) |

## Architecture

### Backend Pattern

For the current API surface, module map, core flows, Telegram advisor mode, internal jobs, and database constraints, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

The backend follows a layered architecture:

```
app/
  api/
    dependencies.py          ← FastAPI Depends() factories
    routes/                  ← APIRouter endpoints
  bot/                       ← Telegram-specific handlers
  core/                      ← config, telegram_auth
  integrations/              ← external clients (Supabase, Telegram)
  repositories/              ← database access layer
  schemas/                   ← Pydantic models (v2)
  services/                  ← business logic
  main.py                    ← FastAPI app entry
```

**Rules:**
- Routes call services and repositories, never the database client directly.
- Repositories extend `BaseRepository` and receive a `SupabaseClient` (real or fake).
- Advisor chat history is stored through `advisor_chat_repository.py`; see the architecture data model for details.
- All protected API endpoints use `get_current_user` dependency.
- All data queries must scope by `user_id`.
- Use `Annotated[Type, Depends(factory)]` for FastAPI dependencies.
- Use `pydantic-settings` for configuration (never `os.getenv` directly).
- Use Pydantic v2 patterns only: `model_config = ConfigDict(from_attributes=True)`, `field_validator`, no `class Config`.

### Frontend Pattern

```
frontend/src/
  api/                       ← typed Axios helpers for each domain
  components/                ← one file per component (flat, no folders yet)
  utils/                     ← currency.ts
  App.tsx                    ← auth bootstrap + page navigation/cache
  main.tsx
  styles.css                 ← all global styles
```

**Rules:**
- Components are flat files in `components/`, not nested folders (until a component needs 3+ sibling files).
- Data fetching lives in components via `useEffect`/`useCallback`.
- Visited Mini App pages may stay mounted for lightweight cache; use explicit refresh keys when related data becomes stale.
- Dashboard, Budget, and AI Advisor use the user's `cashflow_period_start_day` setting for their current period.
- Token from local storage, sent via `Authorization: Bearer <jwt>` header.
- All API calls go through typed helpers in `src/api/`.
- No UI library — use existing CSS classes or add new ones to `styles.css`.
- Use `Intl.NumberFormat("id-ID")` for currency formatting.

### Repository Pattern

Repositories use Supabase's query builder, not raw SQL:

```python
class SomeRepository(BaseRepository):
    table_name = "some_table"

    def do_thing(self, ...) -> Row:
        result = self.table().select("*").eq(...).execute()
        return self.first(result)
```

- `BaseRepository` provides `.table()`, `.first()`, `.rows()` helpers.
- Tests use `FakeSupabaseClient` + `FakeQueryBuilder` from `tests/test_repositories.py` (not mocks).
- `FakeSupabaseClient` does NOT enforce unique constraints — check duplicates in route or test explicitly.

## Coding Conventions

### Python

- **Type hints:** Always. Use `from __future__ import annotations` in test files.
- **Imports:** `ruff` enforces sorted imports. `from app.core.config import settings` at module level is ok even though it triggers env loading — use `@patch.dict("os.environ", {…})` in tests that import such modules.
- **Lazy imports:** Use inside functions when module-level import would cause settings initialization at test collection time (e.g., Gemini parser in `transactions.py`).
- **Error handling:** Routes return `HTTPException` with Indonesian detail messages. Services raise Python exceptions (e.g., `ValueError`). Never let raw exceptions reach the client.
- **Tests:** Use `pytestmark = pytest.mark.asyncio`. Tests use `FakeSupabaseClient` from `test_repositories.py`. FastAPI route tests use `TestClient` + `app.dependency_overrides`. Clear overrides in `finally` blocks.
- **Decimal handling:** All amounts are `Decimal`. When converting to response, use `float()` in the schema/Pydantic model. `amount <= 0` is invalid.

### TypeScript / React

- **Strict mode:** `tsconfig.json` has `"strict": true`.
- **Components:** Function components only. Use `useState`/`useEffect`/`useCallback`.
- **Auth state:** Three-state discriminated union: `loading | authenticated | denied`.
- **Error handling:** All async API calls wrapped in try/catch. 401 → call `onUnauthorized` prop. Others → set error state.
- **Formatting:** `formatRupiah(value: number)` returns `Rp1.500` style strings.
- **No `any`:** Use typed interfaces. Import types from API modules.
- **JSX convention:** Self-closing tags for no-children, `aria-` attributes for interactive elements, semantic HTML.

## Naming Conventions

| Context | Convention | Example |
|---|---|---|
| Backend routes | lowercase with hyphens in URL | `/recent-transactions` |
| Python modules | snake_case | `transactions_repository.py` |
| Python classes | PascalCase | `TransactionsRepository` |
| Python functions | snake_case | `parse_month_param()` |
| Python test functions | snake_case, descriptive | `test_budget_duplicate_rejects_with_conflict` |
| Pydantic schemas | PascalCase, suffix indicates role | `TransactionCreate`, `TransactionOut` |
| FastAPI path params | snake_case | `{transaction_id}` |
| FastAPI query params | snake_case | `?month_start=...` |
| TypeScript interfaces | PascalCase | `DashboardSummary` |
| TypeScript functions | camelCase | `getDashboardSummary()` |
| React components | PascalCase | `DashboardOverview.tsx` |
| CSS classes | kebab-case | `.dashboard-shell` |
| Git commits | conventional commits | `feat: add X`, `fix: handle Y` |
| GitHub issues | `Milestone N: description` | `Milestone 5: Save bot-created transactions` |

## Key Project Rules

### Do
- ✅ Use private-by-default: users cannot self-register.
- ✅ Validate Telegram initData server-side with HMAC. Never trust `initDataUnsafe`.
- ✅ Use `PARSER_CONFIDENCE_THRESHOLD` (0.75 default) to decide rule parser → Gemini fallback → clarification.
- ✅ Call Gemini only after rule parser fails (cost saving).
- ✅ Validate all Gemini output through Pydantic before saving.
- ✅ Enforce guardrails in advisor system prompt (prohibited: investment, crypto, stocks, insurance, loans, tax).
- ✅ Use BackgroundTasks for Telegram webhook processing.
- ✅ Return `{ "ok": true }` from webhook quickly.
- ✅ Save raw Telegram message text with every bot-created transaction.
- ✅ For bot transactions: `source="telegram_chat"`. For Mini App: `source="manual"`, `parser="manual"`.
- ✅ Paginate through all rows when aggregating (dashboard, budget actuals, advisor context) using page-size loops.
- ✅ Use `cashflow_period_start_day` for Dashboard, Budget actuals, and Advisor context; default day 1 preserves calendar-month behavior.
- ✅ Keep all bot/advisors responses in Indonesian.
- ✅ Protect internal job endpoints with `X-Cron-Secret` and `CRON_SECRET`.
- ✅ Use `@patch.dict("os.environ", {…})` in tests that need settings.
- ✅ Run full backend test suite + ruff + frontend build + frontend lint before reporting completion.

### Don't
- ❌ Expose `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, `JWT_SECRET_KEY`, `TELEGRAM_BOT_TOKEN`, or `CRON_SECRET` to frontend.
- ❌ Use `os.getenv()` — use `pydantic-settings`.
- ❌ Use Pydantic v1 patterns (`class Config`, `@validator`, `orm_mode`).
- ❌ Use `@app.on_event("startup"/"shutdown")` — use lifespan.
- ❌ Use `asyncio.create_task` for request-scoped work — use `BackgroundTasks`.
- ❌ Return raw dicts without `response_model`.
- ❌ Use magic numbers for HTTP status codes — use `fastapi.status`.
- ❌ Put all routes in `main.py` — use `APIRouter`.
- ❌ Trust `initDataUnsafe` from the frontend.
- ❌ Call Gemini for high-confidence rule parser results.
- ❌ Let Gemini responses bypass Pydantic validation.
- ❌ Allow advisor to recommend financial products, give tax/legal/investment advice, or guarantee outcomes.
- ❌ Log API keys, tokens, or raw Telegram update payloads.
- ❌ Change test files just to make them pass — tests verify behavior contracts.
- ❌ Introduce new dependencies without checking `pyproject.toml` / `package.json` first.
- ❌ Reintroduce `app.core.defaults.py` — language/currency/timezone come from env-backed `Settings`.

## Database Schema (Key Points)

- `users`: PK uuid, unique `telegram_user_id`, `status` (active/inactive), `onboarding_status` (pending/asking_first_name/asking_last_name/completed), `cashflow_period_start_day` (1-31).
- `transactions`: PK uuid, FK to users, `type` (income/expense), `category` (12 fixed values), `amount` numeric(14,2) > 0, `parser` (rule_based/gemini/manual), `source` (telegram_chat/manual).
- `budgets`: PK uuid, FK to users, unique(user_id, category, month), `monthly_limit` > 0.
- `advisor_insights`: PK uuid, FK to users, `insight_type`, `summary`.
- `conversation_states`: PK uuid, FK to users, `state`, `payload` jsonb, `expires_at`.
- `advisor_chat_messages`: PK uuid, FK to users, `role`, `content`, `source`, `metadata`, `created_at`.
- See [docs/ARCHITECTURE.md#data-model](docs/ARCHITECTURE.md#data-model) for the full current data model, constraints, indexes, triggers, and RPCs.
- Migrations applied manually by maintainer — agent does NOT run migrations.

## Transaction Categories (Fixed Enum)

```text
transportasi, makanan_minuman, tagihan, tempat_tinggal, belanja,
hiburan, utang_cicilan, pendapatan, kesehatan, pendidikan, keluarga, lainnya
```

## Environment Variables

All config comes from env via `Settings` class. Reference `backend/.env.example` for the canonical list. Never commit `.env`.

## Test Patterns (Backend)

- Use `tests/test_repositories.py::FakeSupabaseClient` for repository-level tests.
- Use `TestClient(app)` + `app.dependency_overrides` for API route tests.
- Clear `app.dependency_overrides` in `finally` blocks.
- Mock Gemini with `@patch("google.genai.Client")` and `AsyncMock`.
- Use `@patch.dict("os.environ", _FAKE_ENV)` for tests importing modules with `settings` at module level.
- Name tests descriptively: `test_<what>_<expected_behavior>`.

## Useful Commands

```bash
# Backend
cd backend && source .venv/bin/activate && python -m pytest
cd backend && source .venv/bin/activate && ruff check .
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload

# Frontend
cd frontend && npm run build
cd frontend && npm run lint
cd frontend && npm run dev

# Smoke test (requires deployed backend + requests package)
TELEGRAM_BOT_TOKEN=xxx BASE_URL=https://api.example.com python scripts/smoke_test.py
```

## When Implementing a New Milestone

1. Read the Agent Brief comment on the GitHub issue — it's the contract.
2. Follow TDD: write the test first, see it fail, implement, verify.
3. One vertical slice at a time (test → code, not all tests first).
4. Run existing tests frequently — catch regressions early.
5. After implementation, run full verification suite (`pytest` + `ruff` + `npm run build` + `npm run lint`).
6. Post a Done report and Review Summary to the issue as comments.
7. Commit with `feat:` prefix and `Fixes #NN`, push, close issue.
