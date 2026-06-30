alter table users enable row level security;
alter table transactions enable row level security;
alter table budgets enable row level security;
alter table advisor_insights enable row level security;
alter table conversation_states enable row level security;
alter table advisor_chat_messages enable row level security;

revoke all on table users from public, anon, authenticated;
revoke all on table transactions from public, anon, authenticated;
revoke all on table budgets from public, anon, authenticated;
revoke all on table advisor_insights from public, anon, authenticated;
revoke all on table conversation_states from public, anon, authenticated;
revoke all on table advisor_chat_messages from public, anon, authenticated;

create index if not exists idx_conversation_states_state_expires
  on conversation_states (state, expires_at);

create index if not exists idx_advisor_insights_user_period_created
  on advisor_insights (user_id, period_start, period_end, created_at desc);

create index if not exists idx_transactions_user_date_created
  on transactions (user_id, transaction_date desc, created_at desc);

create index if not exists idx_transactions_user_id
  on transactions (user_id, id);

create or replace function public.claim_expired_conversation_states(
  p_state text,
  p_limit integer default 100,
  p_claim_timeout_seconds integer default 300
)
returns setof public.conversation_states
language sql
security definer
set search_path = ''
as $$
  with candidates as (
    select id
    from public.conversation_states
    where state = p_state
      and expires_at < now()
      and (
        payload->>'timeout_claimed_at' is null
        or (payload->>'timeout_claimed_at')::timestamptz
          < now() - make_interval(secs => p_claim_timeout_seconds)
      )
    order by expires_at
    limit p_limit
    for update skip locked
  ),
  claimed as (
    update public.conversation_states states
    set payload = jsonb_set(
      states.payload,
      '{timeout_claimed_at}',
      to_jsonb(now()::text),
      true
    )
    from candidates
    where states.id = candidates.id
    returning states.*
  )
  select * from claimed;
$$;

revoke all on function public.claim_expired_conversation_states(text, integer, integer)
  from public, anon, authenticated;
grant execute on function public.claim_expired_conversation_states(text, integer, integer)
  to service_role;
