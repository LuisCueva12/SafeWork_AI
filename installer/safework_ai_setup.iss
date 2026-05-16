; ============================================================
;  SafeWork AI v1.0 — Instalador Corporativo
;  Softech Perú
;  Compilar con Inno Setup 6.x: https://jrsoftware.org/isinfo.php
; ============================================================

#define AppName      "SafeWork AI"
#define AppVersion   "1.0"
#define AppPublisher "Softech Perú"
#define AppURL       "https://softech.pe"
#define AppExeName   "SafeWork_AI.exe"
#define AppId        "{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppPublisher}\{#AppName}
DefaultGroupName={#AppPublisher}\{#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputDir=dist\installer
OutputBaseFilename=Instalador_SafeWork_AI_v1.0_SoftechPeru
SetupIconFile=assets\safework_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardResizable=no
ShowLanguageDialog=no
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName} — {#AppPublisher}
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} — Monitor de Ergonomia Postural
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon";     Description: "Crear acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked
Name: "startupicon";     Description: "Iniciar SafeWork AI con Windows";        GroupDescription: "Inicio automático:";  Flags: unchecked

[Files]
Source: "dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENCIA.txt";       DestDir: "{app}"; Flags: ignoreversion
Source: "TERMINOS_Y_CONDICIONES.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}";             Filename: "{app}\{#AppExeName}"; Comment: "Monitor de Ergonomia Postural — Softech Perú"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}";     Filename: "{app}\{#AppExeName}"; Comment: "SafeWork AI — Softech Perú"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExeName}"""; Flags: uninsdeletevalue; Tasks: startupicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Iniciar {#AppName} ahora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
procedure InitializeWizard();
begin
  WizardForm.Caption := 'SafeWork AI v1.0 — Instalador — Softech Perú';
end;
