"""Auth routes — Google ID token or (optional) email session. Returns app JWT."""

from fastapi import APIRouter, HTTPException, Request

from app.api.dependencies import AuthServiceDep
from app.config import settings
from app.models.api.auth import GoogleSignInRequest, SignInRequest, SignInResponse
from app.models.api.users import UserResponse
from app.rate_limit import limiter
from app.services.auth.google_tokens import InvalidGoogleTokenError, verify_google_id_token
from app.services.auth.jwt import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _to_user_response(user) -> UserResponse:
    return UserResponse(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
    )


def _require_email_auth() -> None:
    if not settings.auth_allow_email:
        raise HTTPException(
            status_code=403,
            detail="Email sign-in is disabled. Use Google sign-in.",
        )


@router.post("/session", response_model=SignInResponse)
@limiter.limit(settings.rate_limit_auth)
async def create_session(
    request: Request,
    body: SignInRequest,
    auth: AuthServiceDep,
) -> SignInResponse:
    """
    Sign in or create an account via email (dev/tests only when AUTH_ALLOW_EMAIL=true).
    """
    _require_email_auth()
    try:
        user, is_new = auth.sign_in_or_register(body.name, body.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    token = create_access_token(user.user_id, user.email)

    return SignInResponse(
        user=_to_user_response(user),
        is_new_user=is_new,
        auth_provider=auth.provider_name,
        token=token,
    )


@router.post("/google", response_model=SignInResponse)
@limiter.limit(settings.rate_limit_auth)
async def create_google_session(
    request: Request,
    body: GoogleSignInRequest,
    auth: AuthServiceDep,
) -> SignInResponse:
    """Verify a Google ID token, upsert the app user, and return an app JWT."""
    if not settings.google_client_id.strip():
        raise HTTPException(
            status_code=503,
            detail="Google sign-in is not configured.",
        )

    try:
        identity = verify_google_id_token(body.id_token)
    except InvalidGoogleTokenError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    try:
        user, is_new = auth.sign_in_or_register(identity["name"], identity["email"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    token = create_access_token(user.user_id, user.email)

    return SignInResponse(
        user=_to_user_response(user),
        is_new_user=is_new,
        auth_provider="google",
        token=token,
    )
