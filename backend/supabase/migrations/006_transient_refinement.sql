-- One-run extraction hint (cleared after run completes; not part of saved workflow prompt)

alter table workflow_runs add column if not exists transient_refinement text;
