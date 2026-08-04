"""User domain models."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UserRecord:
    user_id: str
    name: str
    email: str = ""
    created_at: Optional[str] = None
