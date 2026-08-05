"""Supabase Postgres repository — the only module that talks to Supabase tables."""

import logging
from datetime import datetime, timezone
from typing import Optional

from supabase import Client, create_client

from app.config import settings
from app.models.domain.pipeline import PlannedStep
from app.models.domain.run import RunResult, StepRunRecord
from app.models.domain.user import UserRecord
from app.models.domain.workflow import WorkflowRecord, WorkflowSummary
from app.persistence.serialization import planned_steps_from_json, planned_steps_to_json

logger = logging.getLogger("db")

_client: Optional[Client] = None


def _is_configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_secret_key)


def _get_client() -> Client:
    global _client
    if not _is_configured():
        raise RuntimeError("Supabase is not configured")
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_secret_key)
        logger.info("Supabase client initialized")
    return _client


class SupabaseRepository:
    backend_name = "supabase"

    def health_check(self) -> tuple[bool, str]:
        if not _is_configured():
            return False, "not_configured"
        try:
            _get_client().table("users").select("id").limit(1).execute()
            return True, "connected"
        except Exception as e:
            logger.warning("Supabase health check failed: %s", e)
            return False, str(e)

    def save_user(self, user: UserRecord) -> None:
        _get_client().table("users").upsert(
            {"id": user.user_id, "name": user.name, "email": user.email}
        ).execute()

    def get_user(self, user_id: str) -> Optional[UserRecord]:
        resp = (
            _get_client().table("users").select("*").eq("id", user_id).maybe_single().execute()
        )
        if not resp.data:
            return None
        row = resp.data
        return UserRecord(
            user_id=row["id"],
            name=row["name"],
            email=row.get("email") or "",
            created_at=row.get("created_at"),
        )

    def list_users(self) -> list[UserRecord]:
        resp = _get_client().table("users").select("*").order("created_at", desc=True).execute()
        return [
            UserRecord(
                user_id=row["id"],
                name=row["name"],
                email=row.get("email") or "",
                created_at=row.get("created_at"),
            )
            for row in resp.data or []
        ]

    def save_run(self, run: RunResult) -> None:
        now = datetime.now(timezone.utc).isoformat()
        _get_client().table("workflow_runs").upsert(
            {
                "id": run.run_id,
                "workflow_id": run.workflow_id,
                "upload_id": run.upload_id,
                "document_ids": run.document_ids,
                "task_description": run.task_description,
                "status": run.status,
                "planned_steps": planned_steps_to_json(run.planned_steps),
                "result": run.result,
                "error_message": run.error_message,
                "completed_at": now if run.status in ("completed", "failed") else None,
            }
        ).execute()

        _get_client().table("workflow_step_runs").delete().eq("run_id", run.run_id).execute()
        step_rows = [
            {
                "run_id": run.run_id,
                "step_order": step.step_order,
                "agent_type": step.agent_type,
                "status": step.status,
                "output": step.output,
                "error_message": step.error_message,
            }
            for step in run.steps
        ]
        if step_rows:
            _get_client().table("workflow_step_runs").insert(step_rows).execute()

    def get_run(self, run_id: str) -> Optional[RunResult]:
        run_resp = (
            _get_client().table("workflow_runs").select("*").eq("id", run_id).maybe_single().execute()
        )
        if not run_resp.data:
            return None

        row = run_resp.data
        steps_resp = (
            _get_client()
            .table("workflow_step_runs")
            .select("*")
            .eq("run_id", run_id)
            .order("step_order")
            .execute()
        )
        steps = [
            StepRunRecord(
                step_order=step["step_order"],
                agent_type=step["agent_type"],
                status=step["status"],
                output=step.get("output") or {},
                error_message=step.get("error_message"),
            )
            for step in steps_resp.data or []
        ]
        return RunResult(
            run_id=row["id"],
            workflow_id=row.get("workflow_id"),
            upload_id=row["upload_id"],
            document_ids=row.get("document_ids") or [],
            task_description=row.get("task_description") or "",
            status=row["status"],
            steps=steps,
            planned_steps=planned_steps_from_json(row.get("planned_steps")),
            result=row.get("result"),
            error_message=row.get("error_message"),
        )

    def list_runs_by_workflow(self, workflow_id: str) -> list[RunResult]:
        resp = (
            _get_client()
            .table("workflow_runs")
            .select("id")
            .eq("workflow_id", workflow_id)
            .order("created_at", desc=True)
            .execute()
        )
        runs: list[RunResult] = []
        for row in resp.data or []:
            run = self.get_run(row["id"])
            if run is not None:
                runs.append(run)
        return runs

    def save_workflow(self, workflow: WorkflowRecord) -> None:
        _get_client().table("workflows").upsert(
            {
                "id": workflow.workflow_id,
                "user_id": workflow.user_id,
                "name": workflow.name,
                "description": workflow.description,
                "source": workflow.source,
                "task_description": workflow.task_description,
            }
        ).execute()

        _get_client().table("workflow_steps").delete().eq("workflow_id", workflow.workflow_id).execute()
        step_rows = [
            {
                "workflow_id": workflow.workflow_id,
                "step_order": step.step_order,
                "agent_type": step.agent_type,
                "config": step.config,
                "reason": step.reason,
            }
            for step in workflow.steps
        ]
        if step_rows:
            _get_client().table("workflow_steps").insert(step_rows).execute()

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowRecord]:
        wf_resp = (
            _get_client()
            .table("workflows")
            .select("*")
            .eq("id", workflow_id)
            .maybe_single()
            .execute()
        )
        if not wf_resp.data:
            return None

        steps_resp = (
            _get_client()
            .table("workflow_steps")
            .select("*")
            .eq("workflow_id", workflow_id)
            .order("step_order")
            .execute()
        )
        steps = [
            PlannedStep(
                step_order=step["step_order"],
                agent_type=step["agent_type"],
                config=step.get("config") or {},
                reason=step.get("reason") or "",
            )
            for step in steps_resp.data or []
        ]
        row = wf_resp.data
        return WorkflowRecord(
            workflow_id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            description=row.get("description") or "",
            source=row.get("source") or "manual",
            task_description=row.get("task_description") or "",
            steps=steps,
            created_at=row.get("created_at"),
        )

    def list_workflows(self, user_id: Optional[str] = None) -> list[WorkflowSummary]:
        query = _get_client().table("workflows").select("*").order("created_at", desc=True)
        if user_id is not None:
            query = query.eq("user_id", user_id)
        resp = query.execute()

        steps_resp = _get_client().table("workflow_steps").select("workflow_id").execute()
        step_counts: dict[str, int] = {}
        for step in steps_resp.data or []:
            wf_id = step["workflow_id"]
            step_counts[wf_id] = step_counts.get(wf_id, 0) + 1

        return [
            WorkflowSummary(
                workflow_id=row["id"],
                user_id=row["user_id"],
                name=row["name"],
                description=row.get("description") or "",
                source=row.get("source") or "manual",
                step_count=step_counts.get(row["id"], 0),
                created_at=row.get("created_at"),
            )
            for row in resp.data or []
        ]


def is_supabase_configured() -> bool:
    """Used only by registry.py to resolve auto backends."""
    return _is_configured()


def get_supabase_client() -> Client:
    """Shared by SupabaseRepository and SupabaseDocumentRepository only."""
    return _get_client()
