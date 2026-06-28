alter table users
  add column if not exists cashflow_period_start_day integer not null default 1
  check (cashflow_period_start_day between 1 and 31);
