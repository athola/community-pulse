"""Tests for health endpoint."""

from fastapi.testclient import TestClient

from community_pulse.api.app import create_app


def test_health_check() -> None:
    """Test health check returns healthy status."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_current_pulse() -> None:
    """Test current pulse endpoint returns data."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/pulse/current")

    assert response.status_code == 200
    data = response.json()
    assert "topics" in data
    assert "snapshot_id" in data
    assert len(data["topics"]) > 0


def test_pulse_graph() -> None:
    """Test pulse graph endpoint returns nodes and edges."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/pulse/graph")

    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0
