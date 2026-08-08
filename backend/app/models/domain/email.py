"""Email delivery domain models."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class EmailRequest:
    to_email: str
    subject: str
    rows: list[dict[str, Any]]
    pipeline_name: str = ""
    doc_count: int = 0


@dataclass
class EmailResult:
    email_id: str
    status: str
    error_message: Optional[str] = None


class EmailDeliveryError(Exception):
    """Raised when email sending fails."""


@dataclass
class InboundAddress:
    address_id: str
    full_address: str
    user_id: str
    workflow_id: str
    created_at: Optional[str] = None


class InboundAddressNotFoundError(Exception):
    """Raised when inbound address doesn't map to a user/workflow."""
