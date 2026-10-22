; Instalador do PlusEduc (Inno Setup 6). Compile com: python scripts/build_exe.py --installer  (ou --installer --nuitka para o backend compilado)
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6F1D2C54-8E0B-4B0E-9C57-2B5A61D7E301}
AppName=PlusEduc
AppVersion={#AppVersion}
AppPublisher=PlusEduc
DefaultDirName={autopf}\PlusEduc
DefaultGroupName=PlusEduc
DisableProgramGroupPage=yes
; Instalação por usuário: não pede administrador e a pasta fica gravável.
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename=PlusEduc-Setup-{#AppVersion}
SetupIconFile=..\assets\pluseduc.ico
UninstallDisplayIcon={app}\PlusEduc.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
; Quem reabre o app após uma atualização silenciosa é o [Run] abaixo (evita duas janelas).
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar um atalho na Área de Trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "..\dist\PlusEduc\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion createallsubdirs

[Icons]
Name: "{autoprograms}\PlusEduc"; Filename: "{app}\PlusEduc.exe"
Name: "{autodesktop}\PlusEduc"; Filename: "{app}\PlusEduc.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\PlusEduc.exe"; Description: "Abrir o PlusEduc agora"; Flags: nowait postinstall skipifsilent
; Atualização iniciada pelo próprio PlusEduc (/SILENT): reabre o aplicativo já na versão nova.
Filename: "{app}\PlusEduc.exe"; Flags: nowait postinstall skipifnotsilent

; A configuração e o log do usuário (%APPDATA%\PlusEduc) são mantidos ao desinstalar.
