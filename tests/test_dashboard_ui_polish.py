from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_loads_polish_layer_after_main_ui():
    dashboard = (ROOT / "app" / "dashboard.py").read_text(encoding="utf-8")
    assert "full_ui.js" in dashboard
    assert "ui_polish.js" in dashboard


def test_ui_polish_has_compact_controls_and_two_column_integrations():
    ui = (ROOT / "app" / "dashboard" / "ui_polish.js").read_text(encoding="utf-8")
    assert ".btn{width:auto!important" in ui
    assert ".integration-provider-grid,.integration-social-grid{display:grid;grid-template-columns:repeat(2" in ui
    assert ".calendar-form{display:grid" in ui
    assert ".analytics-line-path" in ui


def test_ui_polish_preserves_direct_provider_configuration_action():
    ui = (ROOT / "app" / "dashboard" / "ui_polish.js").read_text(encoding="utf-8")
    assert "Configure provider" in ui
    assert "window.go('settings')" in ui
    assert "Publishing activity trend" in ui
