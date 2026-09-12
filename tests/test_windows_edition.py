from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_desktop_package_contract():
    windows = ROOT / "windows"
    installer = ROOT / "installer" / "AI-Social-Agent.iss"
    workflow = ROOT / ".github" / "workflows" / "windows-installer.yml"

    for name in ("install-agent.ps1", "start-agent.ps1", "stop-agent.ps1", "update-agent.ps1"):
        assert (windows / name).is_file()

    installer_text = installer.read_text(encoding="utf-8")
    assert "AI Social Agent" in installer_text
    assert "PrepareToInstall" in installer_text
    assert "stop-agent.ps1" in installer_text
    assert "ProgramData" in installer_text
    assert "AI-Social-Agent-Setup" in installer_text

    start_text = (windows / "start-agent.ps1").read_text(encoding="utf-8")
    assert "ProgramData" in start_text
    assert "api.pid" in start_text
    assert "worker.pid" in start_text
    assert "uvicorn" in start_text

    stop_text = (windows / "stop-agent.ps1").read_text(encoding="utf-8")
    assert "Stop-ProcessTree" in stop_text
    assert "AI Social Agent.lnk" in stop_text

    update_text = (windows / "update-agent.ps1").read_text(encoding="utf-8")
    assert "ProgramData" in update_text
    assert "Get-FileHash" in update_text
    assert "VERYSILENT" in update_text
    assert "stop-agent.ps1" in update_text

    workflow_text = workflow.read_text(encoding="utf-8")
    assert "Run Python tests" in workflow_text
    assert "Build installer" in workflow_text
    assert "Upload installer" in workflow_text
    assert "workflow_dispatch" in workflow_text
