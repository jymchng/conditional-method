import pytest
import os
from fastapi.testclient import TestClient
from fastapi_auth import app, create_access_token, get_secret_key, JWT_ALGORITHM
from datetime import datetime, timedelta
import jwt

ENVIRONMENT_KEY = "ENVIRONMENT_KEY"


class TestAuthenticationDevelopment:
    """Tests for development environment authentication"""

    @pytest.fixture(autouse=True)
    def setup_environment(self, monkeypatch):
        """Set up development environment for tests"""
        # Save original environment
        self.original_env = os.environ.get(ENVIRONMENT_KEY)
        # Set test environment
        monkeypatch.setenv(ENVIRONMENT_KEY, "development")
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
        return TestClient(app)

    def test_protected_route_no_token(self, client: TestClient):
        """Test accessing protected route without token still works in development"""
        # This will still fail due to FastAPI's HTTPBearer handling
        response = client.get("/protected")
        assert response.status_code == 403  # Bearer scheme still enforced

    def test_protected_route_invalid_token(self, client: TestClient):
        """Test accessing protected route with invalid token works in development"""
        response = client.get(
            "/protected", headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 200
        assert response.json()["user"] == "test_user"  # Default test user

    def test_protected_route_expired_token(self, client: TestClient):
        """Test accessing protected route with expired token works in development"""
        # Create a token that is already expired
        expired = datetime.utcnow() - timedelta(minutes=10)
        token_data = {"sub": "expired_user", "role": "user", "exp": expired.timestamp()}
        token = jwt.encode(token_data, get_secret_key(), algorithm=JWT_ALGORITHM)

        response = client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["user"] == "expired_user"  # Default test user

    def test_admin_endpoint_default_user(self, client: TestClient):
        """Test accessing admin endpoint with default user fails even in development"""
        response = client.get("/admin", headers={"Authorization": "Bearer any-token"})
        assert response.status_code == 403  # Still needs admin role

    def test_admin_endpoint_admin_user(self, client: TestClient):
        """Test accessing admin endpoint with admin role succeeds"""
        token = create_access_token({"sub": "admin_user", "role": "admin"})
        response = client.get("/admin", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        
        assert response.json()["user"] == "admin_user"
