#ifndef MyAppRoot
#define MyAppRoot "..\.."
#endif

#ifndef MyAppName
#define MyAppName "honestTai-Tool-Xianyu"
#endif

#ifndef MyAppVersion
#define MyAppVersion "2.0.0"
#endif

[Setup]
AppId={{7E41F2D9-838F-46C3-A5D0-463E0D5075C5}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=honestTai
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#MyAppRoot}\release\installer
OutputBaseFilename={#MyAppName}-Setup
SetupIconFile={#MyAppRoot}\assets\app-icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "{#MyAppRoot}\release\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加快捷方式:"

[Run]
Filename: "{app}\{#MyAppName}.exe"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent
