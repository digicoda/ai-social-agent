$ErrorActionPreference = 'SilentlyContinue'

$DataRoot = Join-Path $env:ProgramData 'AI Social Agent'
$PidDir = Join-Path $DataRoot 'pids'
$Root = Split-Path -Parent $PSScriptRoot

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

# Kill processes recorded by the agent itself, including their child processes.
foreach ($name in @('worker.pid','api.pid')) {
    $pidFile = Join-Path $PidDir $name
    if (Test-Path $pidFile) {
        $raw = (Get-Content $pidFile -Raw).Trim()
        $agentPid = 0
        if ([int]::TryParse($raw, [ref]$agentPid)) {
            [void]$targets.Add($agentPid)
        }
        Remove-Item $pidFile -Force
    }
}

# Also discover orphaned agent processes when PID files are stale/missing.
foreach ($process in @(Get-CimInstance Win32_Process)) {
    if ($process.ProcessId -eq $PID) { continue }
    $commandLine = [string]$process.CommandLine
    if ($commandLine -and ($commandLine -like "*$Root*" -or $commandLine -like '*AI Social Agent*')) {
        # Never target the installer/uninstaller PowerShell process running this script.
        if ($commandLine -notlike '*stop-agent.ps1*') {
            [void]$targets.Add([int]$process.ProcessId)
        }
    }
}

foreach ($target in @($targets)) {
    Stop-ProcessTree $target
}

# Remove the automatic startup shortcut so uninstall/reinstall cannot resurrect an old process.
$startup = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\AI Social Agent.lnk'
Remove-Item $startup -Force

# Give Windows a moment to release Python/SQLite/log file handles.
Start-Sleep -Milliseconds 800

Write-Host 'AI Social Agent processes stopped and startup entry removed.'