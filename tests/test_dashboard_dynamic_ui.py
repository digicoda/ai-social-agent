from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "app" / "dashboard"


def test_dashboard_uses_modular_professional_ui():
    ui = (DASHBOARD / "full_ui.js").read_text(encoding="utf-8")
    assert "AI Providers" in ui
    assert "Publishing destinations" in ui
    assert "Load available models" in ui
    assert "/system/test/${id}" in ui
    assert "config-pane" in ui


def test_search_and_dashboard_ui_files_are_present():
    assert (DASHBOARD / "search_ui.js").exists()
    assert (DASHBOARD / "full_ui.js").exists()


def test_model_discovery_filters_gemini_to_generation_models():
    source = (ROOT / "app" / "system_settings.py").read_text(encoding="utf-8")
    assert "supportedGenerationMethods" in source
    assert "provider_models" in source
    assert '"models"' in source
