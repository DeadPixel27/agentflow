"""Resource ownership helpers — prevent IDOR on authenticated routes."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException, status

from app.models.api.users import UserResponse
from app.models.domain.run import RunResult
from app.persistence.protocols import DataRepository


def require_self(current_user: UserResponse, user_id: str) -> None:
    """Raise 403 unless the path/body user_id matches the JWT user."""
    if current_user.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this resource.",
        )


def require_workflow_owner(workflow: Any, current_user: UserResponse) -> None:
    """Raise 403 unless the workflow belongs to the current user."""
    owner_id = getattr(workflow, "user_id", None)
    if owner_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this workflow.",
        )


async def resolve_run_owner_id(run: RunResult, repo: DataRepository) -> Optional[str]:
    """
    Resolve who owns a run.

    Prefer run.user_id, then workflow owner, then usage_events linkage.
    """
    if run.user_id:
        return run.user_id

    if run.workflow_id:
        workflow = repo.get_workflow(run.workflow_id)
        if workflow is not None and getattr(workflow, "user_id", None):
            return str(workflow.user_id)

    from app.services.usage.metering import get_user_id_for_run

    return await get_user_id_for_run(run.run_id)


async def require_run_access(
    run: RunResult,
    current_user: UserResponse,
    repo: DataRepository,
) -> None:
    """Raise 403 unless the current user owns the run."""
    owner_id = await resolve_run_owner_id(run, repo)
    if owner_id is None:
        # Legacy runs with no owner linkage — deny rather than open access
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this run.",
        )
    if owner_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this run.",
        )
