param([switch]$CleanInstall)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$DataRoot = Join-Path $env:ProgramData 'AI Social Agent'
$ConfigFile = Join-Path $DataRoot 'config.env'
$RecoveryRoot = Join-Path $DataRoot 'updater'

# A genuinely clean install is required when the application payload is gone but
# persistent ProgramData remains (for example after manually deleting C:\Program Files\AI Social Agent).
$AppPayloadExists = Test-Path (Join-Path $Root 'app\version.py')
if ($CleanInstall -or ((Test-Path $DataRoot) -and -not $AppPayloadExists)) {
    $stop = Join-Path $Root 'windows\stop-agent.ps1'
    if (Test-Path $stop) {
        try { & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $stop } catch {}
    }
    if (Test-Path $DataRoot) {
        Remove-Item $DataRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Find-Python {
    foreach ($candidate in @('py','python')) {
        try {
            $version = & $candidate --version 2>&1
            if ($LASTEXITCODE -eq 0 -and $version -match 'Python 3\.(1[1-9]|[2-9][0-9])') { return $candidate }
        } catch {}
    }
    return $null
}

$Python = Find-Python
if (-not $Python) {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Host 'Python 3.11+ not found. Installing Python with winget...'
        & winget install --id Python.Python.3.11 -e --accept-package-agreements --accept-source-agreements
        $Python = Find-Python
    }
}
if (-not $Python) {
    throw 'Python 3.11+ is required. Install Python 3.11 or newer, then run this installer again.'
}

New-Item -ItemType Directory -Force -Path $DataRoot, (Join-Path $DataRoot 'data'), (Join-Path $DataRoot 'logs'), (Join-Path $DataRoot 'media'), (Join-Path $DataRoot 'pids'), $RecoveryRoot | Out-Null

# Keep a recovery uninstaller outside the application folder so it remains usable
# even if the Program Files directory is manually removed.
$RecoveryUninstaller = Join-Path $RecoveryRoot 'uninstall-agent.ps1'
Copy-Item (Join-Path $Root 'windows\uninstall-agent.ps1') $RecoveryUninstaller -Force

$VenvPath = Join-Path $Root '.venv'
$VenvPython = Join-Path $VenvPath 'Scripts\python.exe'
if (-not (Test-Path $VenvPython)) {
    & $Python -m venv $VenvPath
}

$DepsMarker = Join-Path $VenvPath '.requirements-installed'
$Requirements = Join-Path $Root 'requirements.txt'
$RequirementsHash = (Get-FileHash $Requirements -Algorithm SHA256).Hash
$InstalledHash = if (Test-Path $DepsMarker) { (Get-Content $DepsMarker -Raw).Trim() } else { '' }
if ($InstalledHash -ne $RequirementsHash) {
    & $VenvPython -m pip install -r $Requirements
    Set-Content -Path $DepsMarker -Value $RequirementsHash -Encoding ASCII
} else {
    Write-Host 'Python environment already installed; reusing existing dependencies.'
}

if (-not (Test-Path $ConfigFile)) {
    $session = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    $apiKey = [guid]::NewGuid().ToString('N')
    @"
APP_ENV=development
ADMIN_USERNAME=
ADMIN_PASSWORD=
SESSION_SECRET=$session
INTERNAL_API_KEY=$apiKey
DATABASE_URL=sqlite:///C:/ProgramData/AI Social Agent/data/ai_social_agent.db
GEMINI_API_KEY=
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_AUTHOR_URN=
WORKER_POLL_SECONDS=5
"@ | Set-Content -Encoding UTF8 $ConfigFile
    Write-Host 'First-run account setup is handled in the AI Social Agent dashboard.' -ForegroundColor Yellow
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'windows\start-agent.ps1')
if ($LASTEXITCODE -ne 0) {
    throw 'AI Social Agent could not start. Check the logs in C:\ProgramData\AI Social Agent\logs.'
}
Write-Host 'Installation complete.' -ForegroundColor Green
