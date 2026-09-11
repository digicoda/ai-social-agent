$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$DataRoot = Join-Path $env:ProgramData 'AI Social Agent'
$ConfigFile = Join-Path $DataRoot 'config.env'
$VenvPython = Join-Path $Root '.venv\Scripts\python.exe'
$PidDir = Join-Path $DataRoot 'pids'
$LogDir = Join-Path $DataRoot 'logs'

New-Item -ItemType Directory -Force -Path $PidDir, $LogDir | Out-Null

if (-not (Test-Path $VenvPython)) {
    throw "Python environment is missing. Run windows\install-agent.ps1 first."
}

if (-not (Test-Path $ConfigFile)) {
    throw "First-run configuration is missing. Run windows\install-agent.ps1 first."
}

# Load configuration as process environment variables. Environment variables take
# precedence over the app's local .env file and keep mutable data outside Program Files.
Get-Content $ConfigFile | ForEach-Object {
    if ($_ -match '^\s*([^#=][^=]*)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2], 'Process')
    }
}

$env:PYTHONPATH = $Root

function Test-Health {
    try {
        $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 3 -UseBasicParsing
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Get-RunningProcess([string]$PidFile) {
    if (-not (Test-Path $PidFile)) { return $null }
    try {
        $id = [int](Get-Content $PidFile -Raw).Trim()
        return Get-Process -Id $id -ErrorAction Stop
    } catch {
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        return $null
    }
}

$ApiPidFile = Join-Path $PidDir 'api.pid'
$WorkerPidFile = Join-Path $PidDir 'worker.pid'

if (-not (Test-Health)) {
    $Api = Get-RunningProcess $ApiPidFile
    if (-not $Api) {
        $ApiLog = Join-Path $LogDir 'api.log'
        $ApiErr = Join-Path $LogDir 'api-error.log'
        $Api = Start-Process -FilePath $VenvPython -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $Root -RedirectStandardOutput $ApiLog -RedirectStandardError $ApiErr -PassThru
        Set-Content -Path $ApiPidFile -Value $Api.Id
    }
}

$Worker = Get-RunningProcess $WorkerPidFile
if (-not $Worker) {
    $WorkerLog = Join-Path $LogDir 'worker.log'
    $WorkerErr = Join-Path $LogDir 'worker-error.log'
    $Worker = Start-Process -FilePath $VenvPython -ArgumentList '-m','app.cli','worker','--loop' -WorkingDirectory $Root -RedirectStandardOutput $WorkerLog -RedirectStandardError $WorkerErr -PassThru
    Set-Content -Path $WorkerPidFile -Value $Worker.Id
}

for ($i = 0; $i -lt 30; $i++) {
    if (Test-Health) {
        Start-Process 'http://127.0.0.1:8000/dashboard'
        Write-Host 'AI Social Agent is running.' -ForegroundColor Green
        Write-Host 'Dashboard: http://127.0.0.1:8000/dashboard'
        exit 0
    }
    Start-Sleep -Seconds 1
}

Write-Host 'API did not become healthy. Check:' -ForegroundColor Red
Write-Host (Join-Path $LogDir 'api-error.log')
exit 1
