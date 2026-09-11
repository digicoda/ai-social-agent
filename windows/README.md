# Windows Desktop Edition

This directory adds a Windows-first local runtime without changing the existing application architecture.

## Design rule

The existing Linux/Docker deployment remains unchanged. The Windows edition is an additional delivery target so future approved application changes can be applied to both targets.

## Current bootstrap

Run PowerShell from the repository root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\windows\install-agent.ps1
```

The bootstrap:

1. Requires Python 3.11+.
2. Creates `.venv`.
3. Installs the existing `requirements.txt` dependencies.
4. Creates local data/log/pid/media directories.
5. Creates a first-run `.env` with random local admin/session/API credentials when one does not already exist.
6. Starts the API and worker.
7. Opens the local dashboard after `/health` becomes ready.

## Runtime commands

```powershell
.\windows\start-agent.ps1
.\windows\stop-agent.ps1
```

Dashboard:

```text
http://127.0.0.1:8000/dashboard
```

## Installer roadmap

The planned distributable is `AI-Social-Agent-Setup.exe`, built with the Inno Setup definition under `installer/`. It will package the Windows launcher/bootstrap and application source while keeping runtime data outside the application directory.

## Important compatibility rule

Do not move Windows-specific behavior into the core application unless it is genuinely cross-platform. The same application code should continue to support the existing Docker/Linux deployment.
