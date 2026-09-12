from __future__ import annotations

from app import system_settings


def test_system_settings_persist_and_mask(tmp_path, monkeypatch):
    config = tmp_path / "config.env"
    config.write_text("SESSION_SECRET=test-secret\nGEMINI_API_KEY=existing\n", encoding="utf-8")
    monkeypatch.setenv("AI_SOCIAL_AGENT_CONFIG", str(config))

    before = system_settings.read_settings()
    assert before["gemini_api_key"]["configured"] is True
    assert before["gemini_api_key"]["masked"] == "••••••••"

    after = system_settings.save_settings({
        "ai_provider": "huggingface",
        "gemini_model": "gemini-test",
        "openai_model": "gpt-test",
        "huggingface_model": "deepseek-test",
        "worker_batch_size": "7",
    })
    assert after["ai_provider"] == "huggingface"
    assert after["gemini_model"] == "gemini-test"
    assert after["openai_model"] == "gpt-test"
    assert after["huggingface_model"] == "deepseek-test"
    assert after["worker_batch_size"] == "7"
    assert "GEMINI_API_KEY=existing" in config.read_text(encoding="utf-8")
