create table if not exists advisor_insights (
  id uuid primary key default gen_random_uuid(),

  user_id uuid not null references users(id) on delete cascade,
  period_start date not null,
  period_end date not null,

  insight_type text not null,
  summary text not null,
  generated_by text not null default 'gemini',

  created_at timestamptz not null default now()
);
