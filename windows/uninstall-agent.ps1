param([string]$AppRoot = '')
$ErrorActionPreference = 'Stop'

$Root = if ($AppRoot) { $AppRoot } else { Split-Path -Parent $PSScriptRoot }
$DataRoot = Join-Path $env:ProgramData 'AI Social Agent'
$UninstallerRoot = Join-Path $DataRoot 'updater'
$SelfCopy = Join-Path $UninstallerRoot 'uninstall-agent.ps1'
$CurrentScript = (Resolve-Path $PSCommandPath).Path
$CopiedScript = (Resolve-Path $SelfCopy -ErrorAction SilentlyContinue).Path

New-Item -ItemType Directory -Force -Path $UninstallerRoot | Out-Null

# Always detach the cleanup helper before deleting the live application folder.
if ($CurrentScript -ne $CopiedScript) {
    Copy-Item $CurrentScript $SelfCopy -Force
    $args = "-NoProfile -ExecutionPolicy Bypass -File `"$SelfCopy`" -AppRoot `"$Root`""
    Start-Process powershell.exe -ArgumentList $args -WindowStyle Hidden
    exit 0
}

$stop = Join-Path $Root 'windows\stop-agent.ps1'
if (Test-Path $stop) {
    try { & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $stop } catch {}
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

if ($uninstaller) {
    $exe = $uninstaller.Trim()
    if ($exe.StartsWith('"')) {
        $endQuote = $exe.IndexOf('"', 1)
        if ($endQuote -gt 1) { $exe = $exe.Substring(1, $endQuote - 1) }
    }
    if (Test-Path $exe) {
        # Ask Windows for elevation and wait for the actual Inno Setup uninstaller.
        $process = Start-Process -FilePath $exe -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -Verb RunAs -Wait -PassThru
        if ($process.ExitCode -ne 0) { throw "Uninstaller failed with exit code $($process.ExitCode)." }
        exit 0
    }
}

# Recovery path: the application folder or registry entry may already have been
# deleted manually. Remove the persistent data and remaining application files
# directly so a subsequent installation is genuinely clean.
try {
    $startup = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\AI Social Agent.lnk'
    if (Test-Path $startup) { Remove-Item $startup -Force -ErrorAction SilentlyContinue }
} catch {}

if (Test-Path $Root) {
    Remove-Item $Root -Recurse -Force -ErrorAction SilentlyContinue
}
if (Test-Path $DataRoot) {
    Remove-Item $DataRoot -Recurse -Force -ErrorAction SilentlyContinue
}
