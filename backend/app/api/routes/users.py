"""
Users Route — create users and list their workflows.
"""

from fastapi import APIRouter, HTTPException

from app.api.dependencies import AuthServiceDep, UserServiceDep, WorkflowServiceDep
from app.models.api.users import UserCreateRequest, UserResponse
from app.models.api.workflows import WorkflowSummaryResponse
from app.services.users.user_service import UserNotFoundError

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", response_model=UserResponse)
async def register_user(body: UserCreateRequest, auth: AuthServiceDep) -> UserResponse:
    """Create or restore a user by email (delegates to auth service)."""
    if not body.email.strip():
        raise HTTPException(status_code=400, detail="Email is required")

    user, _ = auth.sign_in_or_register(body.name, body.email)
    return UserResponse(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
    )


@router.get("", response_model=list[UserResponse])
async def list_all_users(users: UserServiceDep) -> list[UserResponse]:
    """List all users."""
    return [
        UserResponse(
            user_id=user.user_id,
            name=user.name,
            email=user.email,
            created_at=user.created_at,
        )
        for user in users.fetch_all_users()
    ]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, users: UserServiceDep) -> UserResponse:
    """Get a user by ID."""
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
) -> list[WorkflowSummaryResponse]:
    """List workflows owned by a user."""
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
