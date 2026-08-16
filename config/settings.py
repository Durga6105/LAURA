"""
LAURA - Application Settings

Centralized configuration for the entire application.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # ------------------------------------------
    # Application
    # ------------------------------------------
    app_name: str = "LAURA"
    app_env: str = "development"
    debug: bool = True

    # ------------------------------------------
    # Gemini
    # ------------------------------------------
    gemini_api_key: str
    gemini_model: str = "gemini-3.6-flash"

    # ------------------------------------------
    # ChromaDB
    # ------------------------------------------
    chroma_persist_directory: str = str(BASE_DIR / "chroma_db")

    # ------------------------------------------
    # Validation
    # ------------------------------------------
    max_validation_iterations: int = 5

    # ------------------------------------------
    # File Storage
    # ------------------------------------------
    rulebook_directory: str = str(BASE_DIR / "data" / "rulebooks")
    nda_directory: str = str(BASE_DIR / "data" / "nda")
    output_directory: str = str(BASE_DIR / "data" / "output")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()