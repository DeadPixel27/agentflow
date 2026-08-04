"""
Health check — simple endpoint to verify the server is running.

Used by: deployment platforms (Railway, etc.) to know the app is alive.
"""

from fastapi import APIRouter

from app.models.api.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse()
