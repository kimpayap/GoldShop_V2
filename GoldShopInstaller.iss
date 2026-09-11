#define MyAppName "GoldShop"
#define MyAppVersion "2.9.0"
#define MyAppPublisher "GoldShop"
#define MyAppExeName "GoldShop.exe"

[Setup]
AppId={{C644B85F-2D33-4B22-AEA2-04E549FEA4DA}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\GoldShop
DefaultGroupName=GoldShop
OutputDir=installer
OutputBaseFilename=GoldShop_Setup_Windows
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "dist\GoldShop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\GoldShop"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\GoldShop"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "สร้างไอคอนบน Desktop"; GroupDescription: "ไอคอนเพิ่มเติม:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "เปิด GoldShop"; Flags: nowait postinstall skipifsilent
