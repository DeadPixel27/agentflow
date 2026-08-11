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

from app.config import settings
from app.persistence.supabase_repository import (
    SupabaseRepository,
    get_supabase_client,
    is_supabase_configured,
)

REQUIRED_TABLES = (
    "users",
    "workflows",
    "workflow_steps",
    "workflow_runs",
    "workflow_step_runs",
)


def _bucket_id(bucket) -> str:
    return str(getattr(bucket, "id", None) or getattr(bucket, "name", "") or "")


def _bucket_is_public(bucket) -> bool:
    return bool(getattr(bucket, "public", False))


def _verify_private_buckets(client) -> list[str]:
    """Assert app buckets exist and are private. Empty list = OK or skipped."""
    names = [
        settings.supabase_documents_bucket,
        settings.supabase_user_templates_bucket,
    ]
    # Preserve order, drop duplicates if env aliases collide
    seen: set[str] = set()
    ordered: list[str] = []
    for name in names:
        if name and name not in seen:
            seen.add(name)
            ordered.append(name)

    try:
        buckets = client.storage.list_buckets()
    except Exception as e:
        print(f"  SKIP storage buckets — could not list ({e})")
        print("    Run supabase/migrations/013_storage_private.sql if Storage is enabled.")
        return []

    by_id = {_bucket_id(b): b for b in buckets if _bucket_id(b)}
    failures: list[str] = []

    for name in ordered:
        bucket = by_id.get(name)
        if bucket is None:
            print(f"  FAIL bucket: {name} — not found")
            failures.append(f"missing bucket {name}")
            continue
        if _bucket_is_public(bucket):
            print(f"  FAIL bucket: {name} — public (must be private)")
            failures.append(f"public bucket {name}")
            continue
        print(f"  OK  bucket: {name} (private)")

    return failures


def main() -> int:
    print("Nexora — Supabase verification\n")

    if not is_supabase_configured():
        print("FAIL: Supabase not configured.")
        print("  Set SUPABASE_URL and SUPABASE_SECRET_KEY in backend/.env")
        print("  See docs/SUPABASE_SETUP.md")
        return 1

    ok, detail = SupabaseRepository().health_check()
    if not ok:
        print(f"FAIL: Cannot reach Supabase — {detail}")
        print("  Check URL/key and that schema.sql was run in SQL Editor.")
        return 1

    print("OK: Connected to Supabase")

    client = get_supabase_client()
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

    bucket_failures = _verify_private_buckets(client)
    if bucket_failures:
        print(f"\nFAIL: Storage bucket issues: {', '.join(bucket_failures)}")
        print("  Create private buckets and run supabase/migrations/013_storage_private.sql")
        print("  See docs/SUPABASE_SETUP.md section 5")
        return 1

    print("\nAll checks passed. Restart uvicorn — /api/health should show persistence=supabase")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
