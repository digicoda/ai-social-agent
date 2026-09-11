$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$DataRoot = Join-Path $env:ProgramData 'AI Social Agent'
$ConfigFile = Join-Path $DataRoot 'config.env'

if (-not (Test-Path $ConfigFile)) {
    [System.Windows.Forms.MessageBox]::Show('First-run configuration was not created. Please check the logs in C:\ProgramData\AI Social Agent\logs.', 'AI Social Agent Setup', 'OK', 'Error') | Out-Null
    exit 1
}

$values = @{}
Get-Content $ConfigFile | ForEach-Object {
    if ($_ -match '^\s*([^#=][^=]*)=(.*)$') {
        $values[$matches[1].Trim()] = $matches[2]
    }
}

$username = if ($values.ContainsKey('ADMIN_USERNAME')) { $values['ADMIN_USERNAME'] } else { 'admin' }
$password = if ($values.ContainsKey('ADMIN_PASSWORD')) { $values['ADMIN_PASSWORD'] } else { '(not found)' }
$url = 'http://127.0.0.1:8000/dashboard'

$message = "AI Social Agent is ready!`r`n`r`nLogin credentials:`r`n`r`nUsername:  $username`r`nPassword:  $password`r`n`r`nDashboard:`r`n$url`r`n`r`nPlease save the password before continuing.`r`n`r`nClick OK to open the dashboard."

$result = [System.Windows.Forms.MessageBox]::Show($message, 'AI Social Agent — Setup Complete', 'OK', 'Information')
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    Start-Process $url
}
