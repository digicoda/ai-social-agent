from pathlib import Path

from app import main
from app.version import APP_VERSION


ROOT = Path(__file__).parents[1]


def test_uninstall_endpoint_exists():
    assert any(route.path == "/system/uninstall" for route in main.app.routes)


def test_uninstall_helper_and_installer_payload_exist():
    helper = ROOT / "windows" / "uninstall-agent.ps1"
    installer = ROOT / "installer" / "AI-Social-Agent.iss"
    assert helper.exists()
    text = installer.read_text(encoding="utf-8")
    assert f'#define AppVersion "{APP_VERSION}"' in text
    assert 'Source: "..\\windows\\*.ps1"' in text


def test_update_workflow_publishes_current_release():
    workflow = (ROOT / ".github" / "workflows" / "windows-installer.yml").read_text(encoding="utf-8")
    assert "publish-v1-3-1:" in workflow
    assert "gh release create v1.3.1" in workflow
    assert "gh release upload v1.3.1" in workflow
