"""Upload ownership registry — binds upload_id to a user."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UploadRecord:
    upload_id: str
    user_id: str
    created_at: Optional[str] = None
