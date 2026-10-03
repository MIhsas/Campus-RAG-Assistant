"""Tests for health endpoints and request tracking.

Covers T002 verification requirements 1-7:
  1. live returns 200 with expected fields
  2. ready returns 503 with business code and Chinese message
  3. request_id is valid UUID, consistent with header, unique per request
  4. client X-Request-ID is not echoed back
  5. unknown path returns 404 with tracking header
  6. OpenAPI includes both health endpoints with 503 on ready
  7. create_app() can be instantiated multiple times, no external dependencies
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from campus_assistant.main import create_app


@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


# --- 1. GET /api/v1/health/live ---

class TestLive:
    def test_returns_200(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health/live")
        assert resp.status_code == 200

    def test_body_fields(self, client: TestClient) -> None:
        data = client.get("/api/v1/health/live").json()
        assert data["status"] == "ok"
        assert data["service"] == "campus-assistant-backend"
        assert data["version"] == "0.1.0"
        assert "request_id" in data

    def test_request_id_is_uuid(self, client: TestClient) -> None:
        data = client.get("/api/v1/health/live").json()
        uuid.UUID(data["request_id"])  # raises on invalid

    def test_request_id_matches_header(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health/live")
        assert resp.headers["X-Request-ID"] == resp.json()["request_id"]


# --- 2. GET /api/v1/health/ready ---

class TestReady:
    def test_returns_503(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health/ready")
        assert resp.status_code == 503

    def test_body_fields(self, client: TestClient) -> None:
        data = client.get("/api/v1/health/ready").json()
        assert data["status"] == "not_ready"
        assert data["code"] == "KNOWLEDGE_BASE_NOT_CONFIGURED"
        assert data["message"] == "知识库尚未配置"
        assert data["retryable"] is False

    def test_request_id_is_uuid(self, client: TestClient) -> None:
        data = client.get("/api/v1/health/ready").json()
        uuid.UUID(data["request_id"])

    def test_request_id_matches_header(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health/ready")
        assert resp.headers["X-Request-ID"] == resp.json()["request_id"]


# --- 3. Request IDs are unique ---

class TestRequestIdUniqueness:
    def test_consecutive_ids_differ(self, client: TestClient) -> None:
        id1 = client.get("/api/v1/health/live").json()["request_id"]
        id2 = client.get("/api/v1/health/live").json()["request_id"]
        assert id1 != id2


# --- 4. Client-supplied X-Request-ID is not echoed ---

class TestClientRequestIdNotEchoed:
    def test_custom_header_ignored(self, client: TestClient) -> None:
        fake_id = "00000000-0000-0000-0000-aaaaaaaaaaaa"
        resp = client.get("/api/v1/health/live", headers={"X-Request-ID": fake_id})
        assert resp.headers["X-Request-ID"] != fake_id
        assert resp.json()["request_id"] != fake_id


# --- 5. Unknown path returns 404 with tracking header ---

class TestNotFound:
    def test_404_has_request_id_header(self, client: TestClient) -> None:
        resp = client.get("/api/v1/nonexistent")
        assert resp.status_code == 404
        assert "X-Request-ID" in resp.headers
        # Validate it's a real UUID
        uuid.UUID(resp.headers["X-Request-ID"])


# --- 6. OpenAPI schema includes both endpoints with 503 ---

class TestOpenApiSchema:
    def test_live_in_schema(self, client: TestClient) -> None:
        schema = client.get("/openapi.json").json()
        assert "/api/v1/health/live" in schema["paths"]

    def test_ready_in_schema(self, client: TestClient) -> None:
        schema = client.get("/openapi.json").json()
        assert "/api/v1/health/ready" in schema["paths"]

    def test_ready_declares_503(self, client: TestClient) -> None:
        schema = client.get("/openapi.json").json()
        ready_path = schema["paths"]["/api/v1/health/ready"]
        get_op = ready_path["get"]
        assert "503" in get_op["responses"]


# --- 7. create_app() can be instantiated multiple times ---

class TestAppFactory:
    def test_multiple_instances(self) -> None:
        app1 = create_app()
        app2 = create_app()
        assert app1 is not app2
        # Both should work
        c1 = TestClient(app1)
        c2 = TestClient(app2)
        assert c1.get("/api/v1/health/live").status_code == 200
        assert c2.get("/api/v1/health/ready").status_code == 503

    def test_no_external_dependency(self) -> None:
        """App can be created and serve requests without network, DB, or keys."""
        app = create_app()
        c = TestClient(app)
        resp = c.get("/api/v1/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
