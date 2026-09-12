; AI Social Agent Windows installer
; In-place upgrade installer: stops the running agent, replaces application
; files, and preserves persistent ProgramData data/config/logs/media.

#define AppName "AI Social Agent"
#define AppVersion "1.2.2"
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
CloseApplications=yes
RestartApplications=no
SetupIconFile=AI-Social-Agent.ico
UninstallDisplayIcon={app}\AI-Social-Agent.ico

[Files]
Source: "..\app\*"; DestDir: "{app}\app"; Flags: recursesubdirs ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\windows\*.ps1"; DestDir: "{app}\windows"; Flags: ignoreversion
Source: "AI-Social-Agent.ico"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{commonappdata}\AI Social Agent"
Name: "{commonappdata}\AI Social Agent\data"
Name: "{commonappdata}\AI Social Agent\logs"
Name: "{commonappdata}\AI Social Agent\media"
Name: "{commonappdata}\AI Social Agent\pids"

[Icons]
Name: "{group}\AI Social Agent"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\windows\start-agent.ps1"""; WorkingDir: "{app}"; IconFilename: "{app}\AI-Social-Agent.ico"
Name: "{autodesktop}\AI Social Agent"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\windows\start-agent.ps1"""; WorkingDir: "{app}"; IconFilename: "{app}\AI-Social-Agent.ico"
Name: "{userappdata}\Microsoft\Windows\Start Menu\Programs\Startup\AI Social Agent"; Filename: "powershell.exe"; Parameters: "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""{app}\windows\start-agent.ps1"""; WorkingDir: "{app}"; IconFilename: "{app}\AI-Social-Agent.ico"
Name: "{group}\Uninstall AI Social Agent"; Filename: "{uninstallexe}"; IconFilename: "{app}\AI-Social-Agent.ico"

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  StopScript: String;
  StartupLink: String;
begin
  Result := '';
  NeedsRestart := False;

  StopScript := ExpandConstant('{app}\windows\stop-agent.ps1');
  StartupLink := ExpandConstant('{userappdata}\Microsoft\Windows\Start Menu\Programs\Startup\AI Social Agent.lnk');

  if FileExists(StopScript) then
    Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
      '-NoProfile -ExecutionPolicy Bypass -File "' + StopScript + '"',
      ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode);

  if FileExists(StartupLink) then
    DeleteFile(StartupLink);

  { Persistent ProgramData is deliberately NOT deleted during upgrades. }
end;

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\windows\install-agent.ps1"""; WorkingDir: "{app}"; Flags: waituntilterminated
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\windows\start-agent.ps1"""; WorkingDir: "{app}"; Flags: waituntilterminated postinstall

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\windows\stop-agent.ps1"""; Flags: runhidden waituntilterminated

[UninstallDelete]
Type: filesandordirs; Name: "{commonappdata}\AI Social Agent"
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{userappdata}\Microsoft\Windows\Start Menu\Programs\Startup\AI Social Agent.lnk"
