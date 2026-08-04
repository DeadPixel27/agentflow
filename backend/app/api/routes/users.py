"""
Users Route — create users and list their workflows.
"""

from fastapi import APIRouter, HTTPException

from app.models.api.users import UserCreateRequest, UserResponse
from app.models.api.workflows import WorkflowSummaryResponse
from app.services.users.user_service import UserNotFoundError, create_user, fetch_all_users, fetch_user
from app.services.workflows.workflow_service import fetch_workflows_for_user

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", response_model=UserResponse)
async def register_user(body: UserCreateRequest) -> UserResponse:
    """Create a user (no auth yet — ID is used to scope workflows)."""
    user = create_user(body.name, email=body.email)
    return UserResponse(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
    )


@router.get("", response_model=list[UserResponse])
async def list_all_users() -> list[UserResponse]:
    """List all users."""
    return [
        UserResponse(
            user_id=user.user_id,
            name=user.name,
            email=user.email,
            created_at=user.created_at,
        )
        for user in fetch_all_users()
    ]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str) -> UserResponse:
    """Get a user by ID."""
    try:
        user = fetch_user(user_id)
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return UserResponse(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
    )


@router.get("/{user_id}/workflows", response_model=list[WorkflowSummaryResponse])
async def list_user_workflows(user_id: str) -> list[WorkflowSummaryResponse]:
    """List workflows owned by a user."""
    try:
        workflows = fetch_workflows_for_user(user_id)
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
        for item in workflows
    ]
