"""Shared pytest fixtures.

Every fixture uses ``tmp_path`` so the test suite never touches developer
data directories.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aegisops.api.app import create_app
from aegisops.config.settings import Settings


@pytest.fixture()
def settings(tmp_path) -> Settings:
    """Settings pointing at an isolated temporary data tree."""
    data_dir = tmp_path / "data"
    return Settings(
        _env_file=None,
        data_dir=data_dir,
        fixtures_dir=tmp_path / "fixtures",
        skills_dir=tmp_path / "skills",
        environment="test",
        llm_api_key=None,
        tracing_enabled=True,
    )


@pytest.fixture()
def app(settings):
    """FastAPI application bound to the isolated settings."""
    return create_app(settings)


@pytest.fixture()
def client(app):
    """Synchronous HTTP test client."""
    with TestClient(app) as test_client:
        yield test_client
