from app.config import Settings
from app.readiness import check_readiness


def test_worker_polling_configuration_is_valid(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'db.sqlite'}",
        worker_poll_seconds=60,
    )
    assert settings.worker_poll_seconds > 0
    assert check_readiness(settings)["status"] == "ready"


def test_production_readiness_still_requires_api_key(tmp_path):
    settings = Settings(
        app_env="production",
        internal_api_key="",
        database_url=f"sqlite:///{tmp_path / 'db.sqlite'}",
    )
    assert check_readiness(settings)["status"] == "not_ready"
