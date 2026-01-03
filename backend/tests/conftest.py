from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from dotenv import load_dotenv

from planproof.config import reload_settings

# Load environment variables from .env file
load_dotenv()


@pytest.fixture(autouse=True)
def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure required settings are available for unit tests."""
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=key;EndpointSuffix=core.windows.net")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/planproof")
    monkeypatch.setenv("AZURE_DOCINTEL_ENDPOINT", "https://example.com/docintel")
    monkeypatch.setenv("AZURE_DOCINTEL_KEY", "fake-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.com/openai")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fake-key")
    monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "test-deployment")
    reload_settings()
