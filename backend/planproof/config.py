"""
Configuration management module.

Loads settings from .env file, validates required variables, and centralizes
configuration access across the application. Uses Pydantic for type-safe
configuration with automatic environment variable parsing.

All configuration values are loaded from environment variables (or .env file).
Required variables must be set or the application will fail to start.
"""

import os
import json
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings use Field aliases to map to uppercase environment variable names
    (e.g., DATABASE_URL). The .env file should contain these uppercase variable names.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields in .env that aren't in the model
    )

    # Azure Storage
    azure_storage_connection_string: str = Field(..., alias="AZURE_STORAGE_CONNECTION_STRING")
    azure_storage_container_inbox: str = Field(default="inbox", alias="AZURE_STORAGE_CONTAINER_INBOX")
    azure_storage_container_artefacts: str = Field(default="artefacts", alias="AZURE_STORAGE_CONTAINER_ARTEFACTS")
    azure_storage_container_logs: str = Field(default="logs", alias="AZURE_STORAGE_CONTAINER_LOGS")

    # PostgreSQL
    database_url: str = Field(..., alias="DATABASE_URL")

    # Azure Document Intelligence
    azure_docintel_endpoint: str = Field(..., alias="AZURE_DOCINTEL_ENDPOINT")
    azure_docintel_key: str = Field(..., alias="AZURE_DOCINTEL_KEY")

    # Azure OpenAI
    azure_openai_endpoint: str = Field(..., alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(..., alias="AZURE_OPENAI_API_KEY")
    azure_openai_api_version: str = Field(default="2024-02-15-preview", alias="AZURE_OPENAI_API_VERSION")
    azure_openai_chat_deployment: str = Field(..., alias="AZURE_OPENAI_CHAT_DEPLOYMENT")

    # Optional: Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=True, alias="LOG_JSON")

    # Feature flags
    enable_extraction_cache: bool = Field(default=True, alias="ENABLE_EXTRACTION_CACHE")
    enable_db_writes: bool = Field(default=True, alias="ENABLE_DB_WRITES")
    enable_llm_gate: bool = Field(default=True, alias="ENABLE_LLM_GATE")

    # DocIntel execution flags
    docintel_use_url: bool = Field(default=True, alias="DOCINTEL_USE_URL")
    docintel_page_parallelism: int = Field(default=1, alias="DOCINTEL_PAGE_PARALLELISM")
    docintel_pages_per_batch: int = Field(default=5, alias="DOCINTEL_PAGES_PER_BATCH")

    # LLM context limits
    llm_context_max_chars: int = Field(default=6000, alias="LLM_CONTEXT_MAX_CHARS")
    llm_context_max_blocks: int = Field(default=80, alias="LLM_CONTEXT_MAX_BLOCKS")
    llm_field_context_max_chars: int = Field(default=4000, alias="LLM_FIELD_CONTEXT_MAX_CHARS")
    llm_field_context_max_blocks: int = Field(default=30, alias="LLM_FIELD_CONTEXT_MAX_BLOCKS")

    # Retry policy
    azure_retry_max_attempts: int = Field(default=3, alias="AZURE_RETRY_MAX_ATTEMPTS")
    azure_retry_base_delay_s: float = Field(default=0.5, alias="AZURE_RETRY_BASE_DELAY_S")

    # API Configuration
    api_cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003", "http://localhost:8501"],
        alias="API_CORS_ORIGINS"
    )
    api_keys: list[str] = Field(default_factory=list, alias="API_KEYS")
    jwt_secret_key: str = Field(default="", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=60, alias="JWT_EXPIRATION_MINUTES")
    officer_roles: list[str] = Field(default=["officer", "admin", "reviewer", "planner"], alias="OFFICER_ROLES")

    @field_validator("api_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v) -> list[str]:
        """Parse CORS origins from JSON string or return list as-is."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Fall back to comma-separated parsing
                return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the standard levels."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment (useful for testing)."""
    global _settings
    _settings = Settings()
    return _settings
