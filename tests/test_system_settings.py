from __future__ import annotations

from app import system_settings
from app.config import get_settings


def test_system_settings_persist_and_mask(tmp_path, monkeypatch):
    config = tmp_path / "config.env"
    config.write_text("SESSION_SECRET=test-secret\nGEMINI_API_KEY=existing\n", encoding="utf-8")
    monkeypatch.setenv("AI_SOCIAL_AGENT_CONFIG", str(config))
    get_settings.cache_clear()

    before = system_settings.read_settings()
    assert before["gemini_api_key"]["configured"] is True
    assert before["gemini_api_key"]["masked"] == "••••••••"

    after = system_settings.save_settings({"gemini_model": "gemini-test", "worker_batch_size": "7"})
    assert after["gemini_model"] == "gemini-test"
    assert after["worker_batch_size"] == "7"
    assert "GEMINI_API_KEY=existing" in config.read_text(encoding="utf-8")
    get_settings.cache_clear()
