from pathlib import Path

from app import main
from app.version import APP_VERSION


ROOT = Path(__file__).parents[1]


def test_uninstall_endpoint_exists():
    routes = []
    for route in main.app.routes:
        routes.append(getattr(route, "path", ""))
        for nested in getattr(getattr(route, "routes", None), "__iter__", lambda: iter(()))():
            routes.append(getattr(nested, "path", ""))
    assert "/system/uninstall" in routes


def test_uninstall_helper_and_installer_payload_exist():
    helper = ROOT / "windows" / "uninstall-agent.ps1"
    installer = ROOT / "installer" / "AI-Social-Agent.iss"
    install_script = ROOT / "windows" / "install-agent.ps1"
    assert helper.exists()
    assert install_script.exists()
    text = installer.read_text(encoding="utf-8")
    assert f'#define AppVersion "{APP_VERSION}"' in text
    assert 'Source: "..\\windows\\*.ps1"' in text


def test_clean_install_removes_stale_programdata():
    text = (ROOT / "windows" / "install-agent.ps1").read_text(encoding="utf-8")
    assert "-CleanInstall" in text
    assert "-not $AppPayloadExists" in text
    assert "Remove-Item $DataRoot -Recurse -Force" in text
    assert "updater" in text


def test_uninstall_has_recovery_cleanup_path():
    text = (ROOT / "windows" / "uninstall-agent.ps1").read_text(encoding="utf-8")
    assert "if ($uninstaller)" in text
    assert "Remove-Item $Root -Recurse -Force" in text
    assert "Remove-Item $DataRoot -Recurse -Force" in text


def test_update_workflow_publishes_current_release():
    workflow = (ROOT / ".github" / "workflows" / "windows-installer.yml").read_text(encoding="utf-8")
    assert "publish-v1-3-2:" in workflow
    assert "gh release create v1.3.2" in workflow
    assert "gh release upload v1.3.2" in workflow


def test_profile_analyzer_fix_is_loaded():
    dashboard = (ROOT / "app" / "dashboard.py").read_text(encoding="utf-8")
    assert "profile_analyzer_fix.js" in dashboard
    assert (ROOT / "app" / "dashboard" / "profile_analyzer_fix.js").exists()
