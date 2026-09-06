; ==============================================================================
; TermCoder Inno Setup Script
; Builds a Windows standalone installer that installs TermCoder, registers
; global commands ('ai', 'termcoder') in PATH, and provides direct Windows Terminal
; shortcuts on Desktop and Start Menu.
; ==============================================================================

#define MyAppName "TermCoder"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "TermCoder AI"
#define MyAppURL "https://build.nvidia.com"
#define MyAppExeName "bin\termcoder-wt.cmd"

[Setup]
; Unique application GUID for updates & uninstalls
AppId={{C8E19602-5FD4-4B2E-9D72-887E8F9467AB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=TermCoder-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ChangesEnvironment=yes
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "addtopath"; Description: "Add TermCoder to User PATH (enables running 'ai' and 'termcoder' in any terminal)"; GroupDescription: "Environment Integration:"

[Files]
; Package all staged application files
Source: "dist\TermCoder\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Desktop and Start Menu shortcuts launch directly in Windows Terminal
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{%USERPROFILE}"; Comment: "Launch TermCoder in Windows Terminal"
Name: "{autoprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{%USERPROFILE}"; Comment: "Launch TermCoder in Windows Terminal"
Name: "{autoprograms}\{#MyAppName}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
; Option to launch directly into Windows Terminal after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: shellexec nowait postinstall skipifsilent

[Code]
const
    EnvironmentKey = 'Environment';

procedure AddToPath();
var
    BinDir, OldPath, NewPath: string;
begin
    BinDir := ExpandConstant('{app}\bin');
    if RegQueryStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'Path', OldPath) then
    begin
        if Pos(UpperCase(BinDir), UpperCase(OldPath)) = 0 then
        begin
            if (OldPath <> '') and (OldPath[Length(OldPath)] <> ';') then
                OldPath := OldPath + ';';
            NewPath := OldPath + BinDir;
            RegWriteStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'Path', NewPath);
        end;
    end
    else
    begin
        RegWriteStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'Path', BinDir);
    end;
end;

procedure RemoveFromPath();
var
    BinDir, OldPath: string;
    P: Integer;
begin
    BinDir := ExpandConstant('{app}\bin');
    if RegQueryStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'Path', OldPath) then
    begin
        P := Pos(UpperCase(BinDir), UpperCase(OldPath));
        if P > 0 then
        begin
            if (P + Length(BinDir) <= Length(OldPath)) and (OldPath[P + Length(BinDir)] = ';') then
                Delete(OldPath, P, Length(BinDir) + 1)
            else if (P > 1) and (OldPath[P - 1] = ';') then
                Delete(OldPath, P - 1, Length(BinDir) + 1)
            else
                Delete(OldPath, P, Length(BinDir));
            RegWriteStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'Path', OldPath);
        end;
    end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
    if CurStep = ssPostInstall then
    begin
        if WizardIsTaskSelected('addtopath') then
            AddToPath();
    end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
    if CurUninstallStep = usPostUninstall then
    begin
        RemoveFromPath();
    end;
end;
