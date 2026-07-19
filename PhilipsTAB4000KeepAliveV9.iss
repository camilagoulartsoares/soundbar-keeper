#define MyAppName "Philips TAB4000 KeepAlive V9"
#define MyAppExeName "PhilipsTAB4000KeepAliveV9.exe"
#define MyAppDirName "PhilipsTAB4000KeepAliveV9"

[Setup]
AppId={{0A0E7C13-7D62-4B02-A18F-A9E8C3E26AE7}
AppName={#MyAppName}
AppVersion=9.0.0
DefaultDirName={localappdata}\{#MyAppDirName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=PhilipsTAB4000KeepAliveV9_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "dist\PhilipsTAB4000KeepAliveV9\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "config.example.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "README_INSTALACAO.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "README_TECNICO.md"; DestDir: "{app}"; Flags: ignoreversion

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--cleanup-legacy --skip-startup-task"; Flags: runhidden waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Parameters: "--ensure-startup --skip-startup-task"; Verb: "runas"; Flags: shellexec waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Flags: nowait postinstall skipifsilent runhidden

[UninstallRun]
Filename: "schtasks.exe"; Parameters: "/Delete /TN PhilipsTAB4000KeepAliveV9 /F"; Flags: runhidden waituntilterminated skipifdoesntexist
Filename: "taskkill.exe"; Parameters: "/F /IM PhilipsTAB4000KeepAliveV9.exe"; Flags: runhidden waituntilterminated
