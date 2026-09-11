; AI Social Agent Windows installer
; Build with Inno Setup on a Windows build machine.

#define AppName "AI Social Agent"
#define AppVersion "0.1.0"
#define AppPublisher "DigiCoda"
#define AppExeName "AI-Social-Agent.exe"

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

[Files]
Source: "..\app\*"; DestDir: "{app}\app"; Flags: recursesubdirs ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\.env.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\windows\*.ps1"; DestDir: "{app}\windows"; Flags: ignoreversion

[Dirs]
Name: "{commonappdata}\AI Social Agent"
Name: "{commonappdata}\AI Social Agent\data"
Name: "{commonappdata}\AI Social Agent\logs"
Name: "{commonappdata}\AI Social Agent\media"

[Icons]
Name: "{group}\AI Social Agent"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File \"{app}\windows\start-agent.ps1\""; WorkingDir: "{app}"
Name: "{group}\Uninstall AI Social Agent"; Filename: "{uninstallexe}"

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File \"{app}\windows\install-agent.ps1\""; WorkingDir: "{app}"; Flags: waituntilterminated runascurrentuser
Filename: "http://127.0.0.1:8000/dashboard"; Flags: shellexec postinstall skipifsilent
