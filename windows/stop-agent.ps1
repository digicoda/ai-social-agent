$ErrorActionPreference = 'SilentlyContinue'

$DataRoot = Join-Path $env:ProgramData 'AI Social Agent'
$PidDir = Join-Path $DataRoot 'pids'
$Root = Split-Path -Parent $PSScriptRoot
$RootPattern = $Root.Replace('\','\\')

function Get-DescendantPids([int]$ParentPid) {
    $children = @(Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $ParentPid })
    $result = @()
    foreach ($child in $children) {
        $result += $child.ProcessId
        $result += Get-DescendantPids $child.ProcessId
    }
    return $result
}

function Stop-ProcessTree([int]$ProcessId) {
    if ($ProcessId -le 0 -or $ProcessId -eq $PID) { return }
    $descendants = @(Get-DescendantPids $ProcessId)
    foreach ($childPid in ($descendants | Sort-Object -Descending -Unique)) {
        Stop-Process -Id $childPid -Force
    }
    Stop-Process -Id $ProcessId -Force
}

$targets = New-Object System.Collections.Generic.HashSet[int]

# Kill processes recorded by the agent itself, including child processes.
foreach ($name in @('worker.pid','api.pid')) {
    $pidFile = Join-Path $PidDir $name
    if (Test-Path $pidFile) {
        $raw = (Get-Content $pidFile -Raw).Trim()
        $agentPid = 0
        if ([int]::TryParse($raw, [ref]$agentPid)) { [void]$targets.Add($agentPid) }
        Remove-Item $pidFile -Force
    }
}

# Discover orphaned API/worker Python processes even if PID files are stale.
foreach ($process in @(Get-CimInstance Win32_Process)) {
    if ($process.ProcessId -eq $PID) { continue }
    $commandLine = [string]$process.CommandLine
    if (-not $commandLine) { continue }
    $isAgent = ($commandLine -like "*$Root*") -or
               ($commandLine -match '(?i)uvicorn\s+app\.main:app') -or
               ($commandLine -match '(?i)app\.cli["'']?\s+worker')
    if ($isAgent -and $commandLine -notlike '*stop-agent.ps1*' -and $commandLine -notlike '*update-agent.ps1*') {
        [void]$targets.Add([int]$process.ProcessId)
    }
}

foreach ($target in @($targets)) { Stop-ProcessTree $target }

# Remove automatic startup so an old process cannot resurrect during uninstall/upgrade.
$startup = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\AI Social Agent.lnk'
Remove-Item $startup -Force

# Wait until agent processes have actually exited and Windows can release file handles.
for ($attempt = 1; $attempt -le 20; $attempt++) {
    $running = @(Get-CimInstance Win32_Process | Where-Object {
        $cmd = [string]$_.CommandLine
        $_.ProcessId -ne $PID -and $cmd -and (
            ($cmd -like "*$Root*") -or
            ($cmd -match '(?i)uvicorn\s+app\.main:app') -or
            ($cmd -match '(?i)app\.cli["'']?\s+worker')
        ) -and $cmd -notlike '*stop-agent.ps1*' -and $cmd -notlike '*update-agent.ps1*'
    })
    if ($running.Count -eq 0) { break }
    foreach ($p in $running) { Stop-Process -Id $p.ProcessId -Force }
    Start-Sleep -Milliseconds 500
}

Start-Sleep -Milliseconds 500
Write-Host 'AI Social Agent processes stopped and file handles released.'
