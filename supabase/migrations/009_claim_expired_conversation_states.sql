create or replace function claim_expired_conversation_states(
  p_state text,
  p_limit integer default 100,
  p_claim_timeout_seconds integer default 300
)
returns setof conversation_states
language sql
security definer
set search_path = public
as $$
  with candidates as (
    select id
    from conversation_states
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
    update conversation_states states
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
