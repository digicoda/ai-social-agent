from fastapi.testclient import TestClient

from app import main
from app.config import Settings


def test_health_endpoint_is_public():
    client = TestClient(main.app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ai-social-agent"}


def test_readiness_endpoint_reports_database_state(monkeypatch, tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'db.sqlite'}")
    monkeypatch.setattr(main, "get_settings", lambda: settings)

    client = TestClient(main.app)
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert {item["name"] for item in response.json()["checks"]} == {"database", "configuration"}


def test_readiness_endpoint_requires_internal_key_when_configured(monkeypatch, tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'db.sqlite'}",
        internal_api_key="test-secret",
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)

    client = TestClient(main.app)

    assert client.get("/ready").status_code == 401
    assert client.get("/ready", headers={"X-API-Key": "test-secret"}).status_code == 200
