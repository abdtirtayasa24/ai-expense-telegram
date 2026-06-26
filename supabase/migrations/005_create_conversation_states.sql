create table if not exists conversation_states (
  id uuid primary key default gen_random_uuid(),

  user_id uuid not null references users(id) on delete cascade,
  state text not null,
  payload jsonb not null default '{}',
  expires_at timestamptz not null,

  created_at timestamptz not null default now()
);
