"""Shared pytest fixtures for the FastAPI backend tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Make `app.*` imports resolve when pytest is invoked from any cwd
# (sys.path mutation has to happen before importing app.main — ruff E402
# noqa is intentional below).
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)
