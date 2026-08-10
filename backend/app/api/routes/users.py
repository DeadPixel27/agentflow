"""
Users Route — create users and list their workflows.
"""

from fastapi import APIRouter, HTTPException

from app.api.dependencies import AuthServiceDep, CurrentUserDep, UserServiceDep, WorkflowServiceDep
from app.api.ownership import require_self
from app.config import settings
from app.models.api.users import UserCreateRequest, UserResponse
from app.models.api.workflows import WorkflowSummaryResponse
from app.services.usage.metering import get_usage_summary
from app.services.users.user_service import UserNotFoundError

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", response_model=UserResponse)
async def register_user(body: UserCreateRequest, auth: AuthServiceDep) -> UserResponse:
    """Create or restore a user by email (delegates to auth service)."""
    if not settings.auth_allow_email:
        raise HTTPException(
            status_code=403,
            detail="Email sign-in is disabled. Use Google sign-in.",
        )
    if not body.email.strip():
        raise HTTPException(status_code=400, detail="Email is required")

    user, _ = auth.sign_in_or_register(body.name, body.email)
    return UserResponse(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
    )


@router.get("/me/usage")
async def get_my_usage(current_user: CurrentUserDep) -> dict:
    """Get the authenticated user's usage stats for the current month."""
    try:
        return await get_usage_summary(current_user.user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch usage: {e}") from e


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUserDep) -> UserResponse:
    """Get the authenticated user."""
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    users: UserServiceDep,
    current_user: CurrentUserDep,
) -> UserResponse:
    """Get a user by ID (self only)."""
    require_self(current_user, user_id)
    try:
        user = users.fetch_user(user_id)
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return UserResponse(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
    )


@router.get("/{user_id}/workflows", response_model=list[WorkflowSummaryResponse])
async def list_user_workflows(
    user_id: str,
    workflows: WorkflowServiceDep,
    current_user: CurrentUserDep,
) -> list[WorkflowSummaryResponse]:
    """List workflows owned by the authenticated user."""
    require_self(current_user, user_id)
    try:
        items = workflows.fetch_workflows_for_user(user_id)
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return [
        WorkflowSummaryResponse(
            workflow_id=item.workflow_id,
            user_id=item.user_id,
            name=item.name,
            description=item.description,
            source=item.source,
            step_count=item.step_count,
            created_at=item.created_at,
        )
        for item in items
    ]
