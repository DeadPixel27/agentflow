-- Per-run extraction prompt (template base + user refinements; templates table unchanged)

alter table workflow_runs add column if not exists template_id text;
alter table workflow_runs add column if not exists extraction_prompt text;

alter table workflows add column if not exists extraction_prompt text;

create index if not exists idx_workflow_runs_template_id on workflow_runs(template_id);
