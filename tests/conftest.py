"""
Shared pytest fixtures and configuration.
Sets PYTHONPATH so imports work correctly from the tests directory.
"""
import sys
import os

# Add backend to path so app.* imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Inject safe test environment variables for all tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017")
    monkeypatch.setenv("MAX_ITERATIONS", "3")
    monkeypatch.setenv("QUALITY_THRESHOLD", "0.80")
