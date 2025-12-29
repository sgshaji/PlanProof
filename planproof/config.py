"""
Configuration management - loads .env, validates required variables, centralizes settings.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

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

