-- Migration 003: pipeline template catalog (existing Supabase projects)
-- Run in SQL Editor after prior migrations. Idempotent.

create table if not exists pipeline_templates (
    id text primary key,
    name text not null,
    description text not null default '',
    category text not null default 'general',
    default_task text not null,
    suggested_steps jsonb not null default '[]',
    example_output_fields jsonb not null default '[]',
    sort_order int not null default 0,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_pipeline_templates_category on pipeline_templates(category);
create index if not exists idx_pipeline_templates_active_sort on pipeline_templates(is_active, sort_order);

-- Seeds: see ../seed_templates.sql (run that file next, or paste inserts below)
