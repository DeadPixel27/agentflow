-- Chat refinement: run lineage + cached document text + workflow template link

alter table workflow_runs add column if not exists parent_run_id uuid references workflow_runs(id) on delete set null;
alter table workflow_runs add column if not exists cached_documents jsonb;
alter table workflow_runs add column if not exists refine_summary text;

alter table workflows add column if not exists parent_template_id text;

create index if not exists idx_workflow_runs_parent_run_id on workflow_runs(parent_run_id);
