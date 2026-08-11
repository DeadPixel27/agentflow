"""
Health check — server status and active backends.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.dependencies import RepoDep
from app.config import settings
from app.models.api.health import HealthResponse
from app.persistence import get_data_backend_name, get_document_backend_name

router = APIRouter(tags=["health"])

_MEMORY_IN_PROD_DETAIL = (
    "In-memory persistence is not allowed in production. "
    "Set SUPABASE_URL and SUPABASE_SECRET_KEY (and APP_ENV=production)."
)


@router.get("/api/health", response_model=HealthResponse)
async def health_check(repo: RepoDep):
    ok, detail = repo.health_check()
    data_backend = get_data_backend_name()
    doc_backend = get_document_backend_name()

    if settings.is_production and data_backend == "memory":
        body = HealthResponse(
            status="unhealthy",
            persistence="memory",
            database=detail,
            document_storage=doc_backend,
            detail=_MEMORY_IN_PROD_DETAIL,
        )
        return JSONResponse(status_code=503, content=body.model_dump())

    if data_backend == "memory":
        return HealthResponse(
            persistence="memory",
            database=detail,
            document_storage=doc_backend,
        )

    if ok:
        return HealthResponse(
            persistence=data_backend,
            database=detail,
            document_storage=doc_backend,
        )

    return HealthResponse(
        status="degraded",
        persistence=data_backend,
        database=detail,
        document_storage=doc_backend,
    )
