"""User-owned template version metadata and payloads."""

from dataclasses import dataclass
from typing import Any, Literal, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.domain.pipeline import PlannedStep

ScopeType = Literal["run", "workflow"]


@dataclass
class UserTemplateVersionRecord:
    """Metadata index row — full payload lives in object storage."""

    version_id: str
    scope_type: ScopeType
    scope_id: str
    template_id: str
    storage_key: str
    version_number: int
    refine_summary: str = ""
    parent_version_id: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class UserTemplateVersionPayload:
    """Full snapshot stored in S3 / local user-templates directory."""

    version_id: str
    scope_type: ScopeType
    scope_id: str
    template_id: str
    extraction_prompt: str
    planned_steps: list[dict[str, Any]]
    refine_summary: str = ""
    parent_version_id: Optional[str] = None
    user_message: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class RefinementEvent:
    """Metadata for owner aggregation — no full prompt in Postgres."""

    event_id: str
    template_id: str
    scope_type: ScopeType
    scope_id: str
    version_id: str
    parent_version_id: Optional[str]
    user_message: str
    refine_summary: str = ""
    created_at: Optional[str] = None


@dataclass
class TemplateVersionDetailView:
    """Service-layer view for mapping to API template version detail."""

    payload: UserTemplateVersionPayload
    steps: list["PlannedStep"]
    version_number: int
    is_current: bool


class TemplateVersionNotFoundError(Exception):
    """Raised when a version id does not exist."""


class RunNotFoundForVersionsError(Exception):
    """Raised when a run id does not exist for version operations."""


class RunNotBranchableError(Exception):
    """Raised when a run cannot be branched (e.g. still running)."""
