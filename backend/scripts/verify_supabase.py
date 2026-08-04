#!/usr/bin/env python3
"""
Verify Supabase is configured and the schema exists.

Usage:
  cd backend
  source .venv/bin/activate
  python scripts/verify_supabase.py
"""

import sys
from pathlib import Path

# Allow running as: python scripts/verify_supabase.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.persistence.supabase_client import check_supabase_connection, is_supabase_configured, get_supabase

REQUIRED_TABLES = ("users", "workflows", "workflow_steps", "workflow_runs", "workflow_step_runs")


def main() -> int:
    print("AgentFlow — Supabase verification\n")

    if not is_supabase_configured():
        print("FAIL: Supabase not configured.")
        print("  Set SUPABASE_URL and SUPABASE_SECRET_KEY in backend/.env")
        print("  See backend/SUPABASE_SETUP.md")
        return 1

    ok, detail = check_supabase_connection()
    if not ok:
        print(f"FAIL: Cannot reach Supabase — {detail}")
        print("  Check URL/key and that schema.sql was run in SQL Editor.")
        return 1

    print("OK: Connected to Supabase")

    client = get_supabase()
    if client is None:
        print("FAIL: Client unavailable after connect")
        return 1

    missing = []
    for table in REQUIRED_TABLES:
        try:
            client.table(table).select("*").limit(1).execute()
            print(f"  OK  table: {table}")
        except Exception as e:
            print(f"  FAIL table: {table} — {e}")
            missing.append(table)

    if missing:
        print(f"\nFAIL: Missing tables: {', '.join(missing)}")
        print("  Run backend/supabase/schema.sql in Supabase → SQL Editor")
        return 1

    print("\nAll checks passed. Restart uvicorn — /api/health should show persistence=supabase")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
