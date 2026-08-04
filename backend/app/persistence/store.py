"""
Persistence facade — Supabase when configured, in-memory fallback otherwise.
"""

import logging
from typing import Optional

from app.persistence import memory_store, supabase_store
from app.models.domain.run import RunResult
from app.models.domain.user import UserRecord
from app.models.domain.workflow import WorkflowRecord, WorkflowSummary
from app.persistence.supabase_client import is_supabase_configured

logger = logging.getLogger("db")


def _using_supabase() -> bool:
    if is_supabase_configured():
        return True
    logger.debug("Supabase not configured — using in-memory store")
    return False


def save_user(user: UserRecord) -> None:
    if _using_supabase():
        supabase_store.save_user(user)
    else:
        memory_store.save_user(user)


def get_user(user_id: str) -> Optional[UserRecord]:
    if _using_supabase():
        return supabase_store.get_user(user_id)
    return memory_store.get_user(user_id)


def list_users() -> list[UserRecord]:
    if _using_supabase():
        return supabase_store.list_users()
    return memory_store.list_users()


def save_run(run: RunResult) -> None:
    if _using_supabase():
        supabase_store.save_run(run)
    else:
        memory_store.save_run(run)


def get_run(run_id: str) -> Optional[RunResult]:
    if _using_supabase():
        return supabase_store.get_run(run_id)
    return memory_store.get_run(run_id)


def list_runs_by_workflow(workflow_id: str) -> list[RunResult]:
    if _using_supabase():
        return supabase_store.list_runs_by_workflow(workflow_id)
    return memory_store.list_runs_by_workflow(workflow_id)


def save_workflow(workflow: WorkflowRecord) -> None:
    if _using_supabase():
        supabase_store.save_workflow(workflow)
    else:
        memory_store.save_workflow(workflow)


def get_workflow(workflow_id: str) -> Optional[WorkflowRecord]:
    if _using_supabase():
        return supabase_store.get_workflow(workflow_id)
    return memory_store.get_workflow(workflow_id)


def list_workflows(user_id: Optional[str] = None) -> list[WorkflowSummary]:
    if _using_supabase():
        return supabase_store.list_workflows(user_id=user_id)
    return memory_store.list_workflows(user_id=user_id)
