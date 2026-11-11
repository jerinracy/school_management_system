"""Integration tests for the system health check endpoint."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestHealthCheck:
    def test_health_check_endpoint(self) -> None:
        client = APIClient()
        response = client.get("/api/v1/health/")

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "status" in data
        assert "database" in data
        assert "redis" in data
        assert "version" in data
        assert data["database"] == "connected"
        assert data["version"] == "1.0.0"
