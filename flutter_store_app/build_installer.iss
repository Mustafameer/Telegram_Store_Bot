; Inno Setup Script for Flutter Store App
; This script creates an installer for the Windows Flutter application

#define AppName "Telegram Store App"
#define AppVersion "1.0.0"
#define AppPublisher "Telegram Store Bot"
#define AppExeName "flutter_store_app.exe"
#define BuildDir "build\windows\x64\runner\Release"
#define IconPath "windows\runner\Release\TeleBot.ico"

[Setup]
; App information
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile=
OutputDir=installer
OutputBaseFilename=TelegramStoreApp_Setup
SetupIconFile={#IconPath}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "SkipDebugFiles"; Description: "Skip debug files (.pdb)"; GroupDescription: "Options"; Flags: unchecked

[Files]
; Main executable - Check if exists before including
Source: "{#BuildDir}\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion; Check: FileExists(ExpandConstant('{#SourcePath}\{#BuildDir}\{#AppExeName}'))
; All DLL files (Flutter DLL + plugins and dependencies)
Source: "{#BuildDir}\*.dll"; DestDir: "{app}"; Flags: ignoreversion
; Data directory (flutter_assets, icudtl.dat, app.so) - REQUIRED for app to run
Source: "{#BuildDir}\data\*"; DestDir: "{app}\data"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: DirExists(ExpandConstant('{#SourcePath}\{#BuildDir}\data'))
; Application icon
Source: "{#IconPath}"; DestDir: "{app}"; Flags: ignoreversion; Check: FileExists(ExpandConstant('{#SourcePath}\{#IconPath}'))
; Native assets (if exists) - commented out if not needed
; Source: "{#BuildDir}\native_assets\*"; DestDir: "{app}\native_assets"; Flags: ignoreversion recursesubdirs createallsubdirs
; Any additional files in Release folder (manifest files, etc.) - optional
; Source: "{#BuildDir}\*.manifest"; DestDir: "{app}"; Flags: ignoreversion
; Debug files (.pdb) - optional, usually not included in Release builds
; Source: "{#BuildDir}\*.pdb"; DestDir: "{app}"; Flags: ignoreversion; Check: not IsTaskSelected('SkipDebugFiles')

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\TeleBot.ico"; Comment: "Launch {#AppName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\TeleBot.ico"; Tasks: desktopicon; Comment: "Launch {#AppName}"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\TeleBot.ico"; Tasks: quicklaunchicon; Comment: "Launch {#AppName}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
var
  ExePath: String;
begin
  ExePath := ExpandConstant('{#SourcePath}\{#BuildDir}\{#AppExeName}');
  if not FileExists(ExePath) then
  begin
    MsgBox('Error: Application not built!' + #13#10 + #13#10 +
           'Please build the application first:' + #13#10 +
           '1. Run: flutter build windows --release' + #13#10 +
           '2. Or run: build_release.bat' + #13#10 + #13#10 +
           'Expected file: ' + ExePath, mbError, MB_OK);
    Result := False;
  end
  else
    Result := True;
end;

