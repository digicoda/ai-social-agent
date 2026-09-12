from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_loads_targeted_bugfix_after_existing_layers():
    text = (ROOT / "app" / "dashboard.py").read_text(encoding="utf-8")
    assert "bugfix_ui.js" in text
    assert text.index("workflow_research.js") < text.index("bugfix_ui.js")


def test_web_search_is_not_selectable_until_real_adapter_exists():
    text = (ROOT / "app" / "dashboard" / "bugfix_ui.js").read_text(encoding="utf-8")
    assert "web.disabled=true" in text
    assert "Web Search — unavailable" in text
    assert "not implemented in this build" in text


def test_research_to_content_handoff_and_generation_are_explicit():
    text = (ROOT / "app" / "dashboard" / "bugfix_ui.js").read_text(encoding="utf-8")
    assert "aiSocialSelectedResearch" in text
    assert "/intelligence/run?limit=100" in text
    assert "/content/generate?limit=10" in text
    assert "No new draft was created" in text


def test_installer_has_branded_desktop_and_start_menu_icon():
    text = (ROOT / "installer" / "AI-Social-Agent.iss").read_text(encoding="utf-8")
    assert "SetupIconFile=AI-Social-Agent.ico" in text
    assert "{autodesktop}\\AI Social Agent" in text
    assert "IconFilename: \"{app}\\AI-Social-Agent.ico\"" in text
    assert "Source: \"AI-Social-Agent.ico\"" in text


def test_windows_workflow_generates_icon_before_inno_setup():
    text = (ROOT / ".github" / "workflows" / "windows-installer.yml").read_text(encoding="utf-8")
    assert "python installer/create_icon.py" in text
    assert text.index("Generate branded Windows icon") < text.index("Build installer")
