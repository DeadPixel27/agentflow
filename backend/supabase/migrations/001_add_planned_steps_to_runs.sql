-- Run this if you already created tables before planned_steps was added

alter table workflow_runs
    add column if not exists planned_steps jsonb not null default '[]';
