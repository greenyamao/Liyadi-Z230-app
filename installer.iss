; Inno Setup Script for Liadi Light Controller
#define MyAppName "Liadi Light Controller"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "greenyamao"
#define MyAppURL "https://github.com/greenyamao/light"
#define MyAppExeName "Liadi.exe"

[Setup]
AppId={{D41A25B3-7F2A-4B9A-976E-8CE1E6A174A2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={userpf}\Programs\LiadiLight
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
SetupIconFile=resources\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=dist
OutputBaseFilename=Liadi-v1.0.0-UserSetup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Launch with Windows (minimized to tray)"; GroupDescription: "Other options:"

[Files]
Source: "dist\Liadi\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "LiadiLightController"; ValueData: """{app}\{#MyAppExeName}"" --minimized"; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
