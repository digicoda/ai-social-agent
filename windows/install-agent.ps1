$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$DataRoot = Join-Path $env:ProgramData 'AI Social Agent'
$ConfigFile = Join-Path $DataRoot 'config.env'

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

New-Item -ItemType Directory -Force -Path $DataRoot, (Join-Path $DataRoot 'data'), (Join-Path $DataRoot 'logs'), (Join-Path $DataRoot 'media'), (Join-Path $DataRoot 'pids') | Out-Null

$VenvPath = Join-Path $Root '.venv'
$VenvPython = Join-Path $VenvPath 'Scripts\python.exe'
if (-not (Test-Path $VenvPython)) {
    & $Python -m venv $VenvPath
}

# Do not download/install dependencies on every reinstall.
# The venv is kept under the application directory and is reused when present.
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
    $password = 'admin-' + ([guid]::NewGuid().ToString('N'))
    $session = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    $apiKey = [guid]::NewGuid().ToString('N')
    @"
APP_ENV=development
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$password
SESSION_SECRET=$session
INTERNAL_API_KEY=$apiKey
DATABASE_URL=sqlite:///C:/ProgramData/AI Social Agent/data/ai_social_agent.db
GEMINI_API_KEY=
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_AUTHOR_URN=
WORKER_POLL_SECONDS=5
"@ | Set-Content -Encoding UTF8 $ConfigFile

    Write-Host ''
    Write-Host 'FIRST RUN ADMIN CREDENTIALS' -ForegroundColor Yellow
    Write-Host 'Username: admin'
    Write-Host "Password: $password"
    Write-Host 'Save these credentials somewhere safe.'
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'windows\start-agent.ps1') -NoBrowser

Write-Host ''
Write-Host 'Installation complete.' -ForegroundColor Green
Write-Host 'Dashboard: http://127.0.0.1:8000/dashboard'
