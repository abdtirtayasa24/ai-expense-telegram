create table if not exists users (
  id uuid primary key default gen_random_uuid(),

  telegram_user_id bigint unique not null,
  telegram_username text,
  first_name text,
  last_name text,

  role text not null default 'user'
    check (role in ('admin', 'user')),

  status text not null default 'active'
    check (status in ('active', 'inactive')),

  onboarding_status text not null default 'pending'
    check (
      onboarding_status in (
        'pending',
        'asking_first_name',
        'asking_last_name',
        'completed'
      )
    ),

  language_code text default 'id',
  currency text default 'IDR',
  timezone text default 'Asia/Jakarta',

  registered_by_telegram_id bigint,
  registered_at timestamptz,
  unregistered_at timestamptz,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
