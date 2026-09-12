from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WINDOWS = ROOT / "windows"
INSTALLER = ROOT / "installer" / "AI-Social-Agent.iss"
WORKFLOW = ROOT / ".github" / "workflows" / "windows-installer.yml"


def test_windows_runtime_scripts_exist_and_use_persistent_data_root():
    for name in ("install-agent.ps1", "start-agent.ps1", "stop-agent.ps1", "update-agent.ps1"):
        content = (WINDOWS / name).read_text(encoding="utf-8")
        assert "AI Social Agent" in content
        assert "$env:ProgramData" in content


def test_windows_startup_and_shutdown_are_coordinated():
    start = (WINDOWS / "start-agent.ps1").read_text(encoding="utf-8")
    stop = (WINDOWS / "stop-agent.ps1").read_text(encoding="utf-8")
    assert "api.pid" in start and "worker.pid" in start
    assert "uvicorn" in start and "app.cli" in start
    assert "Stop-ProcessTree" in stop
    assert "AI Social Agent.lnk" in stop


def test_windows_updater_verifies_checksum_before_installing():
    update = (WINDOWS / "update-agent.ps1").read_text(encoding="utf-8")
    assert "Get-FileHash" in update
    assert "Checksum verification failed" in update
    assert "VERYSILENT" in update
    assert "stop-agent.ps1" in update


def test_installer_metadata_and_upgrade_safety():
    content = INSTALLER.read_text(encoding="utf-8")
    assert '#define AppVersion "1.2.2"' in content
    assert 'OutputBaseFilename=AI-Social-Agent-Setup' in content
    assert "PrepareToInstall" in content
    assert "stop-agent.ps1" in content
    assert "Persistent ProgramData is deliberately NOT deleted during upgrades." in content
    assert "{commonappdata}\\AI Social Agent" in content


def test_installer_workflow_builds_only_non_draft_prs_or_pushes():
    content = WORKFLOW.read_text(encoding="utf-8")
    assert "github.event_name != 'pull_request' || github.event.pull_request.draft == false" in content
    assert "Run Python tests" in content
    assert "Build installer" in content
    assert "Upload installer" in content
