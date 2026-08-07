-- User template versions (metadata index) + refinement events for owner aggregation

create table if not exists user_template_versions (
    id uuid primary key,
    scope_type text not null check (scope_type in ('run', 'workflow')),
    scope_id uuid not null,
    parent_version_id uuid references user_template_versions(id) on delete set null,
    template_id text not null,
    storage_key text not null,
    refine_summary text not null default '',
    version_number int not null,
    created_at timestamptz not null default now(),
    unique (scope_type, scope_id, version_number)
);

create index if not exists idx_user_template_versions_scope
    on user_template_versions(scope_type, scope_id, version_number);

create table if not exists refinement_events (
    id uuid primary key default gen_random_uuid(),
    template_id text not null,
    scope_type text not null check (scope_type in ('run', 'workflow')),
    scope_id uuid not null,
    version_id uuid not null references user_template_versions(id) on delete cascade,
    parent_version_id uuid,
    user_message text not null default '',
    refine_summary text not null default '',
    created_at timestamptz not null default now()
);

create index if not exists idx_refinement_events_template
    on refinement_events(template_id, created_at desc);

alter table workflow_runs
    add column if not exists current_template_version_id uuid
        references user_template_versions(id) on delete set null;

alter table workflows
    add column if not exists current_template_version_id uuid
        references user_template_versions(id) on delete set null;
