"""Auth routes — sign in / register via configured auth provider."""

from fastapi import APIRouter, HTTPException

from app.api.dependencies import AuthServiceDep
from app.models.api.auth import SignInRequest, SignInResponse
from app.models.api.users import UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _to_user_response(user) -> UserResponse:
    return UserResponse(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
    )


@router.post("/session", response_model=SignInResponse)
async def create_session(body: SignInRequest, auth: AuthServiceDep) -> SignInResponse:
    """
    Sign in or create an account.

    Users are matched by email in the database (Supabase when configured).
    Same email always returns the same user_id and workflows.
    """
    try:
        user, is_new = auth.sign_in_or_register(body.name, body.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return SignInResponse(
        user=_to_user_response(user),
        is_new_user=is_new,
        auth_provider=auth.provider_name,
    )
