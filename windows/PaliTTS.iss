; Inno Setup script: builds PaliTTS-Setup.exe from PyInstaller's dist\ReadPaliAloud folder.
; Built by .github/workflows/build_windows.yml. Saved as UTF-8 with BOM (for "ā").
#ifndef AppVersion
  #define AppVersion "2.4"
#endif

[Setup]
AppId={{6E4B2C1A-9D3F-4F7B-8A51-2C7D0E5B9A13}
AppName=Read Pāli Aloud
AppVersion={#AppVersion}
AppPublisher=Pali TTS
DefaultDirName={localappdata}\Programs\Read Pali Aloud
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=PaliTTS-Setup
SetupIconFile=..\assets\AppIcon.ico
UninstallDisplayIcon={app}\ReadPaliAloud.exe
UninstallDisplayName=Read Pāli Aloud
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Put an icon on the desktop"; Flags: unchecked

[Files]
Source: "..\dist\ReadPaliAloud\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\assets\AppIcon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "README_Windows.txt"; DestDir: "{app}"; DestName: "Read Me.txt"; Flags: ignoreversion

[InstallDelete]
; files of an older version
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{userprograms}\Read Pāli Aloud"; Filename: "{app}\ReadPaliAloud.exe"; IconFilename: "{app}\AppIcon.ico"
Name: "{userdesktop}\Read Pāli Aloud"; Filename: "{app}\ReadPaliAloud.exe"; IconFilename: "{app}\AppIcon.ico"; Tasks: desktopicon
; Ctrl+Alt+P helper, started at every login
Name: "{userstartup}\Read Pāli Aloud shortcut"; Filename: "{app}\ReadPaliAloud.exe"; Parameters: "--hotkey"; IconFilename: "{app}\AppIcon.ico"

[Run]
Filename: "{app}\ReadPaliAloud.exe"; Parameters: "--hotkey"; Flags: nowait
Filename: "{app}\ReadPaliAloud.exe"; Description: "Open Read Pāli Aloud now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/f /im ReadPaliAloud.exe"; Flags: runhidden; RunOnceId: "StopPaliTTS"

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  { Stop a running copy (the Ctrl+Alt+P helper) so its files can be replaced }
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/f /im ReadPaliAloud.exe', '', SW_HIDE,
       ewWaitUntilTerminated, ResultCode);
  Result := '';
end;
