import pytest
import os
from fastapi.testclient import TestClient
from fastapi_auth import app, create_access_token

ENVIRONMENT_KEY = "ENVIRONMENT_KEY"


class TestAuthenticationProduction:
    """Tests for production environment authentication"""

    @pytest.fixture(autouse=True)
    def setup_environment(self, monkeypatch):
        """Set up production environment for tests"""
        # Save original environment
        self.original_env = os.environ.get(ENVIRONMENT_KEY)
        # Set test environment
        monkeypatch.setenv(ENVIRONMENT_KEY, "production")
        yield
        # Reset environment after test
        if self.original_env:
            monkeypatch.setenv(ENVIRONMENT_KEY, self.original_env)
        else:
            monkeypatch.delenv(ENVIRONMENT_KEY, raising=False)

    @pytest.fixture
    def client(self):
        """Set up test client for tests"""
        # Create a new app instance for each test method
        app.dependency_overrides = {}
        return TestClient(app)

    def test_protected_route_no_token(self, client: TestClient):
        """Test accessing protected route without token fails"""
        response = client.get("/protected")
        assert response.status_code == 403  # No authorization header

    def test_protected_route_invalid_token(self, client: TestClient):
        """Test accessing protected route with invalid token fails"""
        print("ENVIRONMENT: ", os.environ[ENVIRONMENT_KEY])
        response = client.get(
            "/protected", headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401

    def test_protected_route_valid_token_no_role(self, client: TestClient):
        """Test accessing protected route with valid token but no role fails"""
        token = create_access_token({"sub": "test_user"})
        response = client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401
        assert "Invalid token claims" in response.json()["detail"]

    def test_protected_route_valid_token_wrong_role(self, client: TestClient):
        """Test accessing protected route with valid token but wrong role fails"""
        token = create_access_token({"sub": "test_user", "role": "user"})
        response = client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]

    def test_protected_route_valid_token_admin_role(self, client: TestClient):
        """Test accessing protected route with valid admin token succeeds"""
        token = create_access_token({"sub": "admin_user", "role": "admin"})
        response = client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["user"] == "admin_user"
        assert response.json()["role"] == "admin"
