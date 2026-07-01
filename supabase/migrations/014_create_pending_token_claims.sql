-- Pending token claims: lightweight, self-expiring state for unregistered users
-- who have been prompted to send a registration token.  Keyed by
-- telegram_user_id (no FK to users, since the user does not exist yet).

create table if not exists pending_token_claims (
  id uuid primary key default gen_random_uuid(),

  telegram_user_id bigint not null unique,
  chat_id bigint not null,
  expires_at timestamptz not null,

  created_at timestamptz not null default now()
);

create index if not exists idx_pending_token_claims_expires
  on pending_token_claims (expires_at);

alter table pending_token_claims enable row level security;
revoke all on table pending_token_claims from public, anon, authenticated;

-- Lazy cleanup of expired pending claims (called by the cron job).
create or replace function public.delete_expired_pending_token_claims(
  p_limit integer default 200
) returns integer
language sql
security definer
set search_path = ''
as $$
  with candidates as (
    select id
    from public.pending_token_claims
    where expires_at < now()
    order by expires_at
    limit p_limit
    for update skip locked
  ),
  deleted as (
    delete from public.pending_token_claims claims
    using candidates
    where claims.id = candidates.id
    returning claims.id
  )
  select count(*)::integer from deleted;
$$;

revoke all on function public.delete_expired_pending_token_claims(integer)
  from public, anon, authenticated;
grant execute on function public.delete_expired_pending_token_claims(integer)
  to service_role;