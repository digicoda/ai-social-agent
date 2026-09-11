$ErrorActionPreference = 'SilentlyContinue'
$Root = Split-Path -Parent $PSScriptRoot
$PidDir = Join-Path $Root 'data\pids'

foreach ($name in @('worker.pid','api.pid')) {
    $pidFile = Join-Path $PidDir $name
    if (Test-Path $pidFile) {
        $pid = [int](Get-Content $pidFile -Raw).Trim()
        Stop-Process -Id $pid -Force
        Remove-Item $pidFile -Force
    }
}

Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "$Root\.venv\*"
} | Stop-Process -Force

Write-Host 'AI Social Agent stopped.'
