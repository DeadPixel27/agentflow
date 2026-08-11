from typing import Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "agentflow-api"
    persistence: str = "memory"
    database: Optional[str] = None
    document_storage: str = "local"
    detail: Optional[str] = None
