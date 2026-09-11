$ErrorActionPreference = 'SilentlyContinue'
$DataRoot = Join-Path $env:ProgramData 'AI Social Agent'
$PidDir = Join-Path $DataRoot 'pids'

foreach ($name in @('worker.pid','api.pid')) {
    $pidFile = Join-Path $PidDir $name
    if (Test-Path $pidFile) {
        $pid = [int](Get-Content $pidFile -Raw).Trim()
        Stop-Process -Id $pid -Force
        Remove-Item $pidFile -Force
    }
}

Write-Host 'AI Social Agent stopped.'
