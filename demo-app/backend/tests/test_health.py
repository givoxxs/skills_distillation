"""Sanity checks: the app boots and the health route is up."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_openapi_lists_expected_routes(client: TestClient) -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert "/api/health" in paths
    assert "/api/skills" in paths
    assert "/api/skills/{skill}/summary" in paths
    assert "/api/skills/{skill}/skill-md" in paths
    assert "/api/run" in paths
