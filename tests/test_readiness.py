from app.config import Settings
from app.readiness import check_readiness


def test_readiness_accepts_valid_development_configuration(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'db.sqlite'}")
    result = check_readiness(settings)
    assert result["status"] == "ready"
    assert all(item["status"] == "ok" for item in result["checks"])


def test_readiness_requires_api_key_in_production(tmp_path):
    settings = Settings(
        app_env="production",
        internal_api_key="",
        database_url=f"sqlite:///{tmp_path / 'db.sqlite'}",
    )
    result = check_readiness(settings)
    assert result["status"] == "not_ready"
    assert any("INTERNAL_API_KEY" in item["detail"] for item in result["checks"] if item["name"] == "configuration")


def test_readiness_rejects_invalid_linkedin_version(tmp_path):
    settings = Settings(
        linkedin_api_version="2026-08",
        database_url=f"sqlite:///{tmp_path / 'db.sqlite'}",
    )
    result = check_readiness(settings)
    assert result["status"] == "not_ready"
    assert any("YYYYMM" in item["detail"] for item in result["checks"] if item["name"] == "configuration")
