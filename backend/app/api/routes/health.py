"""
Health check — server status and active backends.
"""

from fastapi import APIRouter

from app.api.dependencies import RepoDep
from app.models.api.health import HealthResponse
from app.persistence import get_data_backend_name, get_document_backend_name

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
async def health_check(repo: RepoDep) -> HealthResponse:
    ok, detail = repo.health_check()
    data_backend = get_data_backend_name()
    doc_backend = get_document_backend_name()

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
