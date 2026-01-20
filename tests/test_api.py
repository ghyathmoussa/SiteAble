"""Test API endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from api.api import app
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint returns welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "SiteAble" in data["message"]
    assert "version" in data


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_list_analyzers(client):
    """Test analyzer listing endpoint."""
    response = client.get("/api/analyzers")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "analyzers" in data
    assert data["count"] >= 5  # At least original 5 analyzers


def test_scan_endpoint_invalid_url(client):
    """Test scan endpoint with invalid URL."""
    response = client.post(
        "/api/scan",
        json={"url": "not-a-valid-url"},
    )
    assert response.status_code == 422  # Validation error


def test_scan_endpoint_valid_url(client):
    """Test scan endpoint with valid URL."""
    response = client.post(
        "/api/scan",
        json={"url": "https://example.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "scan_id" in data
    assert data["status"] == "pending"


def test_get_scan_not_found(client):
    """Test getting non-existent scan."""
    response = client.get("/api/scan/nonexistent-id")
    assert response.status_code == 404


def test_list_scans(client):
    """Test listing scans."""
    response = client.get("/api/scans")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_delete_scan_not_found(client):
    """Test deleting non-existent scan."""
    response = client.delete("/api/scan/nonexistent-id")
    assert response.status_code == 404
