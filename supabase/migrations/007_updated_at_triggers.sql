create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists set_users_updated_at on users;
create trigger set_users_updated_at
before update on users
for each row execute function set_updated_at();

drop trigger if exists set_transactions_updated_at on transactions;
create trigger set_transactions_updated_at
before update on transactions
for each row execute function set_updated_at();
