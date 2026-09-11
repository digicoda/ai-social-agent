$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root '.venv\Scripts\python.exe'
$PidDir = Join-Path $Root 'data\pids'
$LogDir = Join-Path $Root 'data\logs'

New-Item -ItemType Directory -Force -Path $PidDir, $LogDir | Out-Null

if (-not (Test-Path $VenvPython)) {
    throw "Python environment is missing. Run windows\install-agent.ps1 first."
}

function Test-Health {
    try {
        $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 3 -UseBasicParsing
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

if (-not (Test-Health)) {
    $ApiLog = Join-Path $LogDir 'api.log'
    $ApiErr = Join-Path $LogDir 'api-error.log'
    $Api = Start-Process -FilePath $VenvPython -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $Root -RedirectStandardOutput $ApiLog -RedirectStandardError $ApiErr -PassThru
    Set-Content -Path (Join-Path $PidDir 'api.pid') -Value $Api.Id
}

$WorkerLog = Join-Path $LogDir 'worker.log'
$WorkerErr = Join-Path $LogDir 'worker-error.log'
$Worker = Start-Process -FilePath $VenvPython -ArgumentList '-m','app.cli','worker','--loop' -WorkingDirectory $Root -RedirectStandardOutput $WorkerLog -RedirectStandardError $WorkerErr -PassThru
Set-Content -Path (Join-Path $PidDir 'worker.pid') -Value $Worker.Id

for ($i = 0; $i -lt 30; $i++) {
    if (Test-Health) {
        Start-Process 'http://127.0.0.1:8000/dashboard'
        Write-Host 'AI Social Agent is running.'
        exit 0
    }
    Start-Sleep -Seconds 1
}

Write-Host 'API did not become healthy. Check data\logs\api-error.log.'
exit 1
