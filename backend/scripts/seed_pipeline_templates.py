#!/usr/bin/env python3
"""CLI: upsert pipeline templates into Supabase (table must exist)."""

from app.persistence.templates.bootstrap import ensure_pipeline_templates_seeded

if __name__ == "__main__":
    ensure_pipeline_templates_seeded()
    print("Done. If the table was missing, run supabase/setup_templates.sql first.")
