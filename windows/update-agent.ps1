param([string]$AppRoot = $env:AI_SOCIAL_AGENT_APP_ROOT)
$ErrorActionPreference = 'Stop'

$Root = if ($AppRoot) { $AppRoot } else { Split-Path -Parent $PSScriptRoot }
$DataRoot = Join-Path $env:ProgramData 'AI Social Agent'
$UpdaterRoot = Join-Path $DataRoot 'updater'
$SelfCopy = Join-Path $UpdaterRoot 'update-agent.ps1'
$Repo = 'digicoda/ai-social-agent'
$AssetName = 'AI-Social-Agent-Setup.exe'
$ChecksumName = 'AI-Social-Agent-Setup.exe.sha256'
$CurrentScript = (Resolve-Path $PSCommandPath).Path
$CopiedScript = (Resolve-Path $SelfCopy -ErrorAction SilentlyContinue).Path

New-Item -ItemType Directory -Force -Path $UpdaterRoot | Out-Null

# Never run the updater from the live application directory because the installer
# replaces that directory. Run a detached copy from ProgramData instead.
if ($CurrentScript -ne $CopiedScript) {
    Copy-Item $CurrentScript $SelfCopy -Force
    Start-Process powershell.exe -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',$SelfCopy -WindowStyle Hidden -Environment @{ AI_SOCIAL_AGENT_APP_ROOT = $Root }
    exit 0
}

$ApiHeaders = @{ 'User-Agent' = 'AI-Social-Agent-Updater'; 'Accept' = 'application/vnd.github+json' }
$Release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -Headers $ApiHeaders -TimeoutSec 15
if (-not $Release.tag_name) { throw 'No published AI Social Agent release is available.' }

$Asset = @($Release.assets) | Where-Object { $_.name -eq $AssetName } | Select-Object -First 1
if (-not $Asset) { throw "Release $($Release.tag_name) does not contain $AssetName." }
$ChecksumAsset = @($Release.assets) | Where-Object { $_.name -eq $ChecksumName } | Select-Object -First 1

$Download = Join-Path $UpdaterRoot $AssetName
$Checksum = Join-Path $UpdaterRoot $ChecksumName
Invoke-WebRequest -Uri $Asset.browser_download_url -OutFile $Download -Headers @{ 'User-Agent' = 'AI-Social-Agent-Updater' } -TimeoutSec 120

if ($ChecksumAsset) {
    Invoke-WebRequest -Uri $ChecksumAsset.browser_download_url -OutFile $Checksum -Headers @{ 'User-Agent' = 'AI-Social-Agent-Updater' } -TimeoutSec 30
    $expected = ((Get-Content $Checksum -Raw) -split '\s+')[0].Trim().ToLowerInvariant()
    $actual = (Get-FileHash $Download -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($expected -ne $actual) { Remove-Item $Download -Force; throw 'Installer checksum verification failed. Update cancelled.' }
}

& (Join-Path $Root 'windows\stop-agent.ps1')

$installer = Start-Process -FilePath $Download -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -Wait -PassThru
if ($installer.ExitCode -ne 0) { throw "Installer failed with exit code $($installer.ExitCode)." }

Start-Process powershell.exe -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $Root 'windows\start-agent.ps1') -WindowStyle Hidden

for ($i = 1; $i -le 30; $i++) {
    try {
        $health = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 2
        if ($health.StatusCode -eq 200) { exit 0 }
    } catch {}
    Start-Sleep -Seconds 1
}
throw 'Update installed, but the local API did not become healthy within 30 seconds.'
