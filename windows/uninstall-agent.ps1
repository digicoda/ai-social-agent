param([string]$AppRoot = '')
$ErrorActionPreference = 'Stop'

$Root = if ($AppRoot) { $AppRoot } else { Split-Path -Parent $PSScriptRoot }
$DataRoot = Join-Path $env:ProgramData 'AI Social Agent'
$UninstallerRoot = Join-Path $DataRoot 'updater'
$SelfCopy = Join-Path $UninstallerRoot 'uninstall-agent.ps1'
$CurrentScript = (Resolve-Path $PSCommandPath).Path
$CopiedScript = (Resolve-Path $SelfCopy -ErrorAction SilentlyContinue).Path

New-Item -ItemType Directory -Force -Path $UninstallerRoot | Out-Null

# The live application directory is removed by Inno Setup, so the detached copy
# must live under ProgramData until the uninstall has completed.
if ($CurrentScript -ne $CopiedScript) {
    Copy-Item $CurrentScript $SelfCopy -Force
    $args = "-NoProfile -ExecutionPolicy Bypass -File `"$SelfCopy`" -AppRoot `"$Root`""
    Start-Process powershell.exe -ArgumentList $args -WindowStyle Hidden
    exit 0
}

$stop = Join-Path $Root 'windows\stop-agent.ps1'
if (Test-Path $stop) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $stop
}

$uninstaller = $null
$roots = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
foreach ($path in $roots) {
    $item = Get-ItemProperty $path -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -eq 'AI Social Agent' } | Select-Object -First 1
    if ($item) {
        $uninstaller = [string]$item.UninstallString
        if ($uninstaller) { break }
    }
}
if (-not $uninstaller) { throw 'AI Social Agent uninstaller could not be found in Windows uninstall registry.' }

$exe = $uninstaller.Trim()
if ($exe.StartsWith('"')) { $exe = $exe.Substring(1,$exe.IndexOf('"',1)-1) }
if (-not (Test-Path $exe)) { throw "AI Social Agent uninstaller is missing: $exe" }

# Ask Windows for elevation when needed and wait for the actual uninstaller.
$process = Start-Process -FilePath $exe -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -Verb RunAs -Wait -PassThru
if ($process.ExitCode -ne 0) { throw "Uninstaller failed with exit code $($process.ExitCode)." }
