-- Migration for existing AgentFlow databases

create table if not exists users (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    email text not null default '',
    created_at timestamptz not null default now()
);

alter table workflows
    add column if not exists user_id uuid references users(id) on delete cascade;

alter table workflow_runs
    add column if not exists document_ids jsonb not null default '[]';

create index if not exists idx_users_email on users(email);
create index if not exists idx_workflows_user_id on workflows(user_id);

-- Backfill: create a default user for existing workflows without an owner
insert into users (id, name, email)
select '00000000-0000-0000-0000-000000000001', 'Default User', ''
where not exists (
    select 1 from users where id = '00000000-0000-0000-0000-000000000001'
);

update workflows
set user_id = '00000000-0000-0000-0000-000000000001'
where user_id is null;

alter table workflows
    alter column user_id set not null;
