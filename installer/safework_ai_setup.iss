; =============================================================================
; INNO SETUP SCRIPT — SafeWork AI v1.0
; Softech Perú © 2026 · Todos los derechos reservados
; Compilar con: Inno Setup Compiler 6.x
; =============================================================================

[Setup]
AppName=SafeWork AI
AppVersion=1.0.0
AppPublisher=Softech Perú S.A.C.
AppPublisherURL=https://softech.pe
AppSupportURL=https://softech.pe/soporte
AppUpdatesURL=https://softech.pe/actualizaciones
DefaultDirName={autopf}\SafeWork AI
DefaultGroupName=SafeWork AI
AllowNoIcons=no
OutputDir=dist\installer
OutputBaseFilename=Instalador_SafeWork_AI_v1.0
SetupIconFile=assets\safework_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardResizable=no
DisableWelcomePage=no
DisableDirPage=no
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\safework_ai.exe

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el Escritorio"; GroupDescription: "Iconos adicionales:"; Flags: checked
Name: "startupentry"; Description: "Iniciar SafeWork AI al encender Windows"; GroupDescription: "Inicio automático:"; Flags: checked

[Files]
Source: "dist\safework_ai.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\safework_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENCIA.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "TERMINOS_Y_CONDICIONES.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\SafeWork AI"; Filename: "{app}\safework_ai.exe"; IconFilename: "{app}\safework_icon.ico"
Name: "{group}\Desinstalar SafeWork AI"; Filename: "{uninstallexe}"
Name: "{autodesktop}\SafeWork AI"; Filename: "{app}\safework_ai.exe"; IconFilename: "{app}\safework_icon.ico"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "SafeWorkAI"; ValueData: """{app}\safework_ai.exe"""; Flags: uninsdeletevalue; Tasks: startupentry

[Run]
Filename: "{app}\safework_ai.exe"; Description: "Iniciar SafeWork AI ahora"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/f /im safework_ai.exe"; Flags: runhidden

[Messages]
WelcomeLabel1=Bienvenido al instalador de SafeWork AI
WelcomeLabel2=Este programa instalará SafeWork AI v1.0 en su computadora.%n%nSafeWork AI es un monitor de ergonomía postural que protege la salud de sus colaboradores mediante visión computacional local.%n%nSe recomienda cerrar todas las aplicaciones antes de continuar.
