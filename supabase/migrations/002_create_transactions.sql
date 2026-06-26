create table if not exists transactions (
  id uuid primary key default gen_random_uuid(),

  user_id uuid not null references users(id) on delete cascade,

  type text not null check (type in ('income', 'expense')),
  name text not null,
  category text not null,
  amount numeric(14, 2) not null check (amount > 0),
  transaction_date date not null,

  note text,
  source text not null default 'telegram_chat',
  parser text not null check (parser in ('rule_based', 'gemini', 'manual')),
  confidence_score numeric(4, 3),
  raw_message text,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
