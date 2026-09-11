; AI Social Agent Windows installer
; Clean-install mode: every installer run stops the old agent and removes the
; previous application files, ProgramData data/config, logs, media and database.
; This intentionally resets the installation instead of preserving old state.

#define AppName "AI Social Agent"
#define AppVersion "1.4.1"
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
Source: "..\windows\*.ps1"; DestDir: "{app}\windows"; Flags: recursesubdirs ignoreversion

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

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  StopScript: String;
  OldAppDir: String;
  DataDir: String;
  StartupLink: String;
  Attempt: Integer;
begin
  Result := '';
  NeedsRestart := False;

  StopScript := ExpandConstant('{app}\windows\stop-agent.ps1');
  OldAppDir := ExpandConstant('{app}');
  DataDir := ExpandConstant('{commonappdata}\AI Social Agent');
  StartupLink := ExpandConstant('{userappdata}\Microsoft\Windows\Start Menu\Programs\Startup\AI Social Agent.lnk');

  { Stop every known/orphaned API and worker process before touching files. }
  if FileExists(StopScript) then
    Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
      '-NoProfile -ExecutionPolicy Bypass -File "' + StopScript + '"',
      ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode);

  { Remove the automatic startup entry so an old process cannot restart. }
  if FileExists(StartupLink) then
    DeleteFile(StartupLink);

  { Remove the complete previous application and persistent state. Retry because
    Windows can briefly retain file handles after Python processes terminate. }
  for Attempt := 1 to 5 do begin
    if DirExists(OldAppDir) then
      DelTree(OldAppDir, True, True, True);
    if DirExists(DataDir) then
      DelTree(DataDir, True, True, True);
    if (not DirExists(OldAppDir)) and (not DirExists(DataDir)) then
      Break;
    Sleep(1000);
  end;

  if DirExists(OldAppDir) or DirExists(DataDir) then begin
    Result := 'AI Social Agent could not be completely stopped/removed. Close any AI Social Agent windows and try again.';
    Exit;
  end;
end;

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\windows\install-agent.ps1"""; WorkingDir: "{app}"; Flags: waituntilterminated
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\windows\show-credentials.ps1"""; WorkingDir: "{app}"; Flags: waituntilterminated postinstall skipifsilent

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\windows\stop-agent.ps1"""; Flags: runhidden waituntilterminated

[UninstallDelete]
Type: filesandordirs; Name: "{commonappdata}\AI Social Agent"
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{userappdata}\Microsoft\Windows\Start Menu\Programs\Startup\AI Social Agent.lnk"
