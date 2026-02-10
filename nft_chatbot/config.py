"""
Configuration management using pydantic-settings.
Loads all settings from .env (project root) and environment variables.
"""

from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root (parent of nft_chatbot/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings loaded from .env and environment variables."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys (set in .env: OPENAI_API_KEY, GROQ_API_KEY — at least one required for chat)
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None

    # Model (.env: OPENAI_MODEL)
    openai_model: str = "gpt-4o"

    # Database (.env: DATABASE_URL)
    database_url: str = "sqlite+aiosqlite:///./nft_chatbot.db"

    # NFT API (.env: NFT_API_BASE)
    nft_api_base: str = "http://localhost:4000"

    # CORS (.env: CORS_ORIGINS, comma-separated)
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Server (.env: HOST, PORT, DEBUG, RELOAD)
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = False


# Global settings instance (loads from .env)
settings = Settings()
