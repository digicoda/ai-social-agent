from pathlib import Path


def test_task9_critical_runtime_modules_exist():
    required = [
        "app/research.py",
        "app/intelligence.py",
        "app/content_workflow.py",
        "app/approval.py",
        "app/scheduling.py",
        "app/publishing.py",
        "app/profile_automation.py",
        "app/profiles.py",
        "app/profile_context.py",
    ]
    missing = [path for path in required if not Path(path).is_file()]
    assert missing == []


def test_task9_ci_keeps_docker_and_windows_validation_workflows():
    workflows = Path(".github/workflows")
    assert (workflows / "docker.yml").is_file()
    assert (workflows / "windows-installer.yml").is_file()
    assert (workflows / "test.yml").is_file()
