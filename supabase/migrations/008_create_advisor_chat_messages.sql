create table if not exists advisor_chat_messages (
  id uuid primary key default gen_random_uuid(),

  user_id uuid not null references users(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  source text not null check (source in ('telegram_chat', 'mini_app')),
  metadata jsonb not null default '{}',

  created_at timestamptz not null default now()
);

create index if not exists idx_advisor_chat_messages_user_created_at
  on advisor_chat_messages (user_id, created_at desc);
