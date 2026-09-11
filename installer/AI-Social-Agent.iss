; AI Social Agent Windows installer
; Existing installations are upgraded in place. ProgramData/config/database are preserved.

#define AppName "AI Social Agent"
#define AppVersion "1.2.1"
#define AppPublisher "DigiCoda"

[Setup]
AppId={{8F4B2C10-2B0A-4D6A-9D2D-AISOCIALAGENT}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\AI Social Agent
DefaultGroupName={#AppName}
OutputDir=output
OutputBaseFilename=AI-Social-Agent-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
WizardStyle=modern
DisableProgramGroupPage=yes

[Files]
Source: "..\app\*"; DestDir: "{app}\app"; Flags: recursesubdirs ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\windows\*.ps1"; DestDir: "{app}\windows"; Flags: ignoreversion

[Dirs]
Name: "{commonappdata}\AI Social Agent"
Name: "{commonappdata}\AI Social Agent\data"
Name: "{commonappdata}\AI Social Agent\logs"
Name: "{commonappdata}\AI Social Agent\media"
Name: "{commonappdata}\AI Social Agent\pids"

[Icons]
Name: "{group}\AI Social Agent"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\windows\start-agent.ps1"""; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 14
Name: "{userappdata}\Microsoft\Windows\Start Menu\Programs\Startup\AI Social Agent"; Filename: "powershell.exe"; Parameters: "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""{app}\windows\start-agent.ps1"""; WorkingDir: "{app}"
Name: "{group}\Uninstall AI Social Agent"; Filename: "{uninstallexe}"

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\windows\stop-agent.ps1"""; WorkingDir: "{app}"; Flags: waituntilterminated skipifsilent
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\windows\install-agent.ps1"""; WorkingDir: "{app}"; Flags: waituntilterminated
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\windows\show-credentials.ps1"""; WorkingDir: "{app}"; Flags: waituntilterminated postinstall skipifsilent

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\windows\stop-agent.ps1"""; Flags: runhidden waituntilterminated

[UninstallDelete]
Type: filesandordirs; Name: "{commonappdata}\AI Social Agent"
