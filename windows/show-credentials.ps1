$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms

$url = 'http://127.0.0.1:8000/dashboard'
$message = "AI Social Agent is ready.`r`n`r`nYour first step is to create the admin username and password directly in the dashboard.`r`n`r`nNo PowerShell-generated credentials are used.`r`n`r`nClick OK to open the local setup screen."
$result = [System.Windows.Forms.MessageBox]::Show($message, 'AI Social Agent — First Run Setup', 'OK', 'Information')
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    Start-Process $url
}
