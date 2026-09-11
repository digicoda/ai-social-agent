$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Find-Python {
    $candidates = @('py','python')
    foreach ($candidate in $candidates) {
        try {
            $version = & $candidate --version 2>&1
            if ($LASTEXITCODE -eq 0 -and $version -match 'Python 3\.(1[1-9]|[2-9][0-9])') { return $candidate }
        } catch {}
    }
    return $null
}

$Python = Find-Python
if (-not $Python) {
    throw 'Python 3.11+ is required. Install Python from python.org and run this installer again.'
}

if (-not (Test-Path '.venv\Scripts\python.exe')) {
    & $Python -m venv .venv
}

& .venv\Scripts\python.exe -m pip install --upgrade pip
& .venv\Scripts\python.exe -m pip install -r requirements.txt

New-Item -ItemType Directory -Force -Path 'data','data\logs','data\pids','media' | Out-Null

if (-not (Test-Path '.env')) {
    $password = [Convert]::ToBase64String((1..24 | ForEach-Object { Get-Random -Maximum 256 }))
    $session = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    $apiKey = [guid]::NewGuid().ToString('N')
    @"
APP_ENV=development
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$password
SESSION_SECRET=$session
INTERNAL_API_KEY=$apiKey
DATABASE_URL=sqlite:///./data/ai_social_agent.db
GEMINI_API_KEY=
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_AUTHOR_URN=
WORKER_POLL_SECONDS=5
"@ | Set-Content -Encoding UTF8 '.env'
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'windows\start-agent.ps1')
Write-Host ''
Write-Host 'Installation complete.'
Write-Host 'Dashboard: http://127.0.0.1:8000/dashboard'
Write-Host 'Credentials are stored in the local .env file.'
