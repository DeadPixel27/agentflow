-- AgentFlow schema — run in Supabase SQL Editor (Dashboard → SQL → New query)

create table if not exists users (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    email text not null default '',
    created_at timestamptz not null default now()
);

create table if not exists workflows (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    name text not null,
    description text not null default '',
    source text not null default 'planner',
    task_description text not null default '',
    created_at timestamptz not null default now()
);

create table if not exists workflow_steps (
    id uuid primary key default gen_random_uuid(),
    workflow_id uuid not null references workflows(id) on delete cascade,
    step_order int not null,
    agent_type text not null,
    config jsonb not null default '{}',
    reason text not null default '',
    unique (workflow_id, step_order)
);

create table if not exists workflow_runs (
    id uuid primary key default gen_random_uuid(),
    workflow_id uuid references workflows(id) on delete set null,
    upload_id text not null,
    document_ids jsonb not null default '[]',
    task_description text not null default '',
    status text not null,
    planned_steps jsonb not null default '[]',
    result jsonb,
    error_message text,
    created_at timestamptz not null default now(),
    completed_at timestamptz
);

create table if not exists workflow_step_runs (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null references workflow_runs(id) on delete cascade,
    step_order int not null,
    agent_type text not null,
    status text not null,
    output jsonb not null default '{}',
    error_message text,
    unique (run_id, step_order)
);

create index if not exists idx_users_email on users(email);
create index if not exists idx_workflows_user_id on workflows(user_id);
create index if not exists idx_workflow_steps_workflow_id on workflow_steps(workflow_id);
create index if not exists idx_workflow_runs_workflow_id on workflow_runs(workflow_id);
create index if not exists idx_workflow_step_runs_run_id on workflow_step_runs(run_id);

-- Pipeline templates (editable catalog — seed via supabase/seed_templates.sql)
create table if not exists pipeline_templates (
    id text primary key,
    name text not null,
    description text not null default '',
    icon text not null default 'file-text',
    category text not null default 'general',
    default_task text not null,
    fields jsonb not null default '[]',
    extraction_instructions text not null default '',
    rules jsonb not null default '[]',
    output_format text not null default 'json',
    suggested_steps jsonb not null default '[]',
    example_output_fields jsonb not null default '[]',
    sort_order int not null default 0,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_pipeline_templates_category on pipeline_templates(category);
create index if not exists idx_pipeline_templates_active_sort on pipeline_templates(is_active, sort_order);
