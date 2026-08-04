"""
Configuration — single place for all settings.

WHY: Instead of hardcoding paths like "uploads/" in 10 files,
     we read them once here. Change one place, everything updates.

HOW: pydantic-settings reads from .env file + environment variables.
"""

from pathlib import Path

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

    # Supabase — persistence (optional; falls back to in-memory)
    supabase_url: str = ""
    supabase_secret_key: str = ""

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


settings = Settings()

# Create upload folder on startup if it doesn't exist
settings.upload_dir.mkdir(parents=True, exist_ok=True)
