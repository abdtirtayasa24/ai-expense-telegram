create table if not exists budgets (
    id uuid primary key default gen_random_uuid(),

    user_id uuid not null references users(id) on delete cascade,
    category text not null,
    monthly_limit numeric(14, 2) not null check (monthly_limit > 0),
    month date not null,

    created_at timestamptz not null default now(),

    unique(user_id, category, month)
);
