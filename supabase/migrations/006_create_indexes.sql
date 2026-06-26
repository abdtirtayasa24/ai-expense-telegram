create index if not exists idx_users_telegram_user_id
on users(telegram_user_id);

create index if not exists idx_users_status
on users(status);

create index if not exists idx_users_onboarding_status
on users(onboarding_status);

create index if not exists idx_transactions_user_date
on transactions(user_id, transaction_date desc);

create index if not exists idx_transactions_user_category
on transactions(user_id, category);

create index if not exists idx_budgets_user_month
on budgets(user_id, month);

create index if not exists idx_conversation_states_user_expires
on conversation_states(user_id, expires_at);
