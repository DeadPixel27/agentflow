"""
Configuration — single place for all settings.

WHY: Instead of hardcoding paths like "uploads/" in 10 files,
     we read them once here. Change one place, everything updates.

HOW: pydantic-settings reads from .env file + environment variables.
"""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory (parent of app/)
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
    )

    # Where uploaded files are saved on disk
    upload_dir: Path = BACKEND_DIR / "uploads"

    # Max file size per upload (in megabytes)
    max_upload_size_mb: int = 10

    # File types we accept
    allowed_extensions: set[str] = {".pdf", ".png", ".jpg", ".jpeg"}

    # Groq LLM — field extraction
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    # Refiner — can use a stronger model if configured
    groq_refiner_model: str = "llama-3.3-70b-versatile"
    # Owner master template synthesis
    groq_owner_model: str = "llama-3.3-70b-versatile"
    admin_api_key: str = ""

    # User template version payloads: auto | local | supabase | aws_s3
    user_template_storage: str = "auto"
    supabase_user_templates_bucket: str = "user-templates"
    # Future AWS S3 swap (USER_TEMPLATE_STORAGE=aws_s3)
    aws_s3_bucket: str = ""
    aws_s3_region: str = ""
    aws_s3_user_templates_prefix: str = "user-templates"

    # Supabase — persistence (optional; falls back to in-memory)
    supabase_url: str = ""
    supabase_secret_key: str = ""

    # Document file storage: auto | local | supabase
    document_storage: str = "auto"
    supabase_documents_bucket: str = "documents"

    # Data persistence: auto | memory | supabase
    persistence_backend: str = "auto"

    # Auth: email = lookup by email (no password); supabase = future Supabase Auth
    auth_backend: str = "email"

    # Comma-separated origins for CORS (e.g. http://localhost:3000,https://app.vercel.app)
    cors_origins: str = "http://localhost:3000"

    # slowapi rate limits (see https://slowapi.readthedocs.io/en/latest/)
    rate_limit_runs_adhoc: str = "10/minute"
    rate_limit_upload: str = "20/minute"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _normalize_cors_origins(cls, value: object) -> str:
        if isinstance(value, list):
            return ",".join(str(item).strip() for item in value if str(item).strip())
        return str(value) if value is not None else "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


settings = Settings()

# Create upload folder on startup if it doesn't exist
settings.upload_dir.mkdir(parents=True, exist_ok=True)
