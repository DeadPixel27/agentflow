"""
Health check — server status and persistence backend.
"""

from fastapi import APIRouter

from app.models.api.health import HealthResponse
from app.persistence.supabase_client import check_supabase_connection, is_supabase_configured

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    if not is_supabase_configured():
        return HealthResponse(persistence="memory", database="not_configured")

    ok, detail = check_supabase_connection()
    if ok:
        return HealthResponse(persistence="supabase", database="connected")

    return HealthResponse(status="degraded", persistence="supabase", database=detail)
