# Application Architecture

## Method

### Architecture Overview

The application uses a Telegram Bot for natural-language transaction input and a Telegram Mini App for dashboard UX.

```plantuml
@startuml
actor User
actor Admin

rectangle "Telegram" {
  component "Telegram Bot Chat" as Bot
  component "Telegram Mini App\nReact" as MiniApp
}

rectangle "Backend\nFastAPI" {
  component "Webhook Controller" as Webhook
  component "Admin Command Handler" as AdminCommands
  component "Onboarding Handler" as Onboarding
  component "Message Parser Service" as Parser
  component "Rule-Based Parser" as RuleParser
  component "Gemini Fallback Parser" as Gemini
  component "Transaction Service" as TxService
  component "Dashboard Service" as Dashboard
  component "Advisor Service" as Advisor
  component "Auth Service\nTelegram initData validation" as Auth
}

database "Supabase PostgreSQL" as DB

Admin --> Bot : /register, /unreg, /users
Bot --> Webhook
Webhook --> AdminCommands
AdminCommands --> DB

User --> Bot : Bayar parkir 5000
Bot --> Webhook
Webhook --> Onboarding
Webhook --> Parser
Parser --> RuleParser
Parser --> Gemini : fallback if low confidence
Parser --> TxService
TxService --> DB
Webhook --> Bot : Indonesian confirmation

User --> MiniApp : Open dashboard
MiniApp --> Auth : raw Telegram initData
Auth --> DB : check active user
Auth --> MiniApp : JWT
MiniApp --> Dashboard
Dashboard --> DB
MiniApp --> Advisor
Advisor --> DB
@enduml
```

### External Documentation References

The AI coding agent should use these official references when implementing integrations:

- Telegram Mini Apps / Web Apps: https://core.telegram.org/bots/webapps
- Telegram Bot API: https://core.telegram.org/bots/api
- Telegram Webhooks: https://core.telegram.org/bots/webhooks
- FastAPI bigger applications and routers: https://fastapi.tiangolo.com/tutorial/bigger-applications/
- FastAPI settings: https://fastapi.tiangolo.com/advanced/settings/
- FastAPI Docker deployment: https://fastapi.tiangolo.com/deployment/docker/
- Supabase Python client: https://supabase.com/docs/reference/python/introduction
- Supabase Python select/pagination: https://supabase.com/docs/reference/python/select
- Gemini structured output: https://ai.google.dev/gemini-api/docs/structured-output
- Gemini API reference: https://ai.google.dev/api

Notes for implementers:
- Telegram Mini App `initData` must be validated on the backend.
- Do not trust frontend-only Telegram user data.
- Supabase service role key must stay server-side only.
- Gemini must be constrained with structured JSON schema and validated again by backend Pydantic models.

---

## System Context

```plantuml
@startuml
actor "Registered User" as User
actor "Super Admin" as Admin

rectangle "Telegram Platform" {
  component "Bot Chat"
  component "Mini App WebView"
}

rectangle "Application Backend\nFastAPI" {
  component "Telegram Webhook"
  component "REST API"
  component "Parser"
  component "Advisor"
  component "Auth"
}

database "Supabase PostgreSQL" as DB
cloud "Gemini API" as Gemini

Admin --> "Bot Chat"
User --> "Bot Chat"
User --> "Mini App WebView"

"Bot Chat" --> "Telegram Webhook"
"Mini App WebView" --> "REST API"

"Telegram Webhook" --> Parser
Parser --> Gemini
Parser --> DB

"REST API" --> Auth
"REST API" --> DB
Advisor --> Gemini
Advisor --> DB
@enduml
```

---

## Core Flows

### Flow 1: Admin Registers User

```plantuml
@startuml
actor Admin
participant Telegram
participant "FastAPI Webhook" as API
database "Supabase PostgreSQL" as DB

Admin -> Telegram : /register 1393634740
Telegram -> API : webhook update
API -> API : validate sender == ADMIN_TELEGRAM_ID
API -> DB : find user by telegram_user_id
alt user does not exist
  API -> DB : insert user status=active onboarding=pending
  API -> Telegram : User berhasil didaftarkan
else user inactive
  API -> DB : update status=active onboarding=pending
  API -> Telegram : User berhasil diaktifkan kembali
else user active
  API -> Telegram : User sudah aktif
end
@enduml
```

### Flow 2: Admin Unregisters User

```plantuml
@startuml
actor Admin
participant Telegram
participant "FastAPI Webhook" as API
database "Supabase PostgreSQL" as DB

Admin -> Telegram : /unreg 1393634740
Telegram -> API : webhook update
API -> API : validate sender == ADMIN_TELEGRAM_ID
API -> API : reject if target == ADMIN_TELEGRAM_ID
API -> DB : find user
alt user active
  API -> DB : update status=inactive, unregistered_at=now()
  API -> Telegram : User berhasil dinonaktifkan
else user inactive
  API -> Telegram : User sudah nonaktif
else not found
  API -> Telegram : User belum terdaftar
end
@enduml
```

### Flow 3: Admin Lists Users

```plantuml
@startuml
actor Admin
participant Telegram
participant "FastAPI Webhook" as API
database "Supabase PostgreSQL" as DB

Admin -> Telegram : /users
Telegram -> API : webhook update
API -> API : validate sender == ADMIN_TELEGRAM_ID
API -> DB : select users order by created_at
DB --> API : users
API -> Telegram : formatted user list
@enduml
```

### Flow 4: Registered User Onboarding

```plantuml
@startuml
actor User
participant Telegram
participant "FastAPI Webhook" as API
database "Supabase PostgreSQL" as DB

User -> Telegram : /start or any first message
Telegram -> API : webhook update
API -> DB : find user by telegram_user_id
alt not registered or inactive
  API -> Telegram : akun belum terdaftar / nonaktif
else onboarding_status == pending
  API -> DB : update onboarding_status=asking_first_name
  API -> Telegram : ask first name
else onboarding_status == asking_first_name
  API -> DB : save first_name, onboarding_status=asking_last_name
  API -> Telegram : ask last name
else onboarding_status == asking_last_name
  API -> DB : save last_name, onboarding_status=completed
  API -> Telegram : onboarding complete
else completed
  API -> Telegram : normal app flow
end
@enduml
```

### Flow 5: User Records Expense

```plantuml
@startuml
actor User
participant Telegram
participant "FastAPI Webhook" as API
participant "Parser Service" as Parser
participant "Rule Parser" as Rule
participant "Gemini Parser" as Gemini
database "Supabase PostgreSQL" as DB

User -> Telegram : Bayar parkir 5000
Telegram -> API : webhook update
API -> DB : check active + onboarded user
API -> Parser : parse message
Parser -> Rule : parse
alt confidence >= threshold
  Rule --> Parser : parsed transaction
else confidence < threshold
  Parser -> Gemini : structured parse
  Gemini --> Parser : parsed transaction
end

alt parsed with good confidence
  API -> DB : insert transaction
  API -> Telegram : Oke, pengeluaran parkir Rp5.000 sudah tercatat.
else needs clarification
  API -> Telegram : ask clarification
end
@enduml
```

### Flow 6: Mini App Authentication

```plantuml
@startuml
actor User
participant "React Mini App" as App
participant "FastAPI Auth API" as API
database "Supabase PostgreSQL" as DB

User -> App : Open dashboard inside Telegram
App -> App : read window.Telegram.WebApp.initData
App -> API : POST /auth/telegram-mini-app
API -> API : validate Telegram initData hash
API -> API : extract telegram_user_id
API -> DB : find active onboarded user
alt user active and onboarded
  API -> App : JWT + user profile
else not active / not onboarded / invalid
  API -> App : 403 Forbidden
end
@enduml
```

---

## Authorization Rules

### Bot Authorization Order

```text
1. Extract telegram_user_id from Telegram update.
2. If message is admin command:
   - /register <telegram_id>
   - /unreg <telegram_id>
   - /users
   Validate sender == ADMIN_TELEGRAM_ID.
3. For normal app usage:
   - find user by telegram_user_id.
4. If user not found or inactive:
   - reject.
5. If user active but onboarding_status != completed:
   - run onboarding flow.
6. If user active and onboarding completed:
   - continue to parser, transaction, advisor, or bot menu flow.
```

### Mini App Authorization Order

```text
1. Frontend reads raw Telegram initData.
2. Frontend sends raw initData to backend.
3. Backend validates initData using bot token.
4. Backend extracts Telegram user ID.
5. Backend checks users table.
6. Backend rejects if user is missing, inactive, or onboarding incomplete.
7. Backend returns JWT if authorized.
8. Frontend sends JWT on subsequent API calls.
```

---

## Data Model

### Entity Relationship Diagram

```plantuml
@startuml
entity users {
  * id : uuid
  --
  telegram_user_id : bigint
  telegram_username : text
  first_name : text
  last_name : text
  role : text
  status : text
  onboarding_status : text
  language_code : text
  currency : text
  timezone : text
  registered_by_telegram_id : bigint
  registered_at : timestamptz
  unregistered_at : timestamptz
  created_at : timestamptz
  updated_at : timestamptz
}

entity transactions {
  * id : uuid
  --
  user_id : uuid
  type : text
  name : text
  category : text
  amount : numeric
  transaction_date : date
  note : text
  source : text
  parser : text
  confidence_score : numeric
  raw_message : text
  created_at : timestamptz
  updated_at : timestamptz
}

entity budgets {
  * id : uuid
  --
  user_id : uuid
  category : text
  monthly_limit : numeric
  month : date
  created_at : timestamptz
}

entity advisor_insights {
  * id : uuid
  --
  user_id : uuid
  period_start : date
  period_end : date
  insight_type : text
  summary : text
  generated_by : text
  created_at : timestamptz
}

entity conversation_states {
  * id : uuid
  --
  user_id : uuid
  state : text
  payload : jsonb
  expires_at : timestamptz
  created_at : timestamptz
}

entity advisor_chat_messages {
  * id : uuid
  --
  user_id : uuid
  role : text
  content : text
  source : text
  metadata : jsonb
  created_at : timestamptz
}

users ||--o{ transactions
users ||--o{ budgets
users ||--o{ advisor_insights
users ||--o{ conversation_states
users ||--o{ advisor_chat_messages
@enduml
```

---