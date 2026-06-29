alter table advisor_insights
  add column if not exists result jsonb,
  add column if not exists context_hash text;

create index if not exists idx_advisor_insights_context_cache
  on advisor_insights (user_id, period_start, period_end, insight_type, context_hash, created_at desc)
  where context_hash is not null;
