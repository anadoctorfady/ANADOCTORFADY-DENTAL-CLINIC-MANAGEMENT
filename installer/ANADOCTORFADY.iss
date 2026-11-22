; ANADOCTORFADY v2 - Inno Setup installer script (Windows only)
; ============================================================
; Build the EXE FIRST (installer\build_exe.bat), then compile this
; script with Inno Setup 6 (free, https://jrsoftware.org/isdl.php)
; or run installer\build_installer.bat, which finds ISCC.exe for you.
; Output: installer\output\ANADOCTORFADY_Setup.exe
;
; DATA SAFETY - the whole point of this installer:
; - The program is installed to %LOCALAPPDATA%\ANADOCTORFADY.
; - Patient data lives in %APPDATA%\ANADOCTORFADY (a DIFFERENT folder,
;   fixed per-user location - see src/config/settings.py). The installer
;   NEVER installs, overwrites or deletes anything there.
; - Reinstall / upgrade only replaces the EXE in %LOCALAPPDATA%.
; - Uninstall removes ONLY the program folder. Patient data is NEVER
;   deleted on uninstall (no UninstallDelete entry for it, ever).
; - First run of the new version migrates an old next-to-EXE database
;   into %APPDATA%\ANADOCTORFADY automatically (verified copy first).
;
; This script CANNOT be compiled on Linux/Mac - Inno Setup is
; Windows-only. Validate on Windows with ISCC.exe (see build_installer.bat).

#define MyAppName "ANADOCTORFADY"
#define MyAppVersion "2.1"
#define MyAppPublisher "Fady Abdulkafy Dadoush"
#define MyAppExeName "ANADOCTORFADY.exe"

[Setup]
AppId={{18C17E6F-5FF4-4093-AD41-B95C4E3EDE67}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Per-user install: no administrator rights needed, because both the
; program folder (%LOCALAPPDATA%) and the data folder (%APPDATA%)
; belong to the current user.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; The EXE is built by installer\build_exe.bat first (32-bit Python
; build runs on x86 AND x64 Windows). Do not force 64-bit mode.
ArchitecturesAllowed=x86compatible x64compatible
OutputDir=output
OutputBaseFilename=ANADOCTORFADY_Setup
SetupIconFile=..\assets\app.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
; License agreement page (round 42): the wizard shows
; license_agreement.txt (bilingual EN/AR, UTF-8 with BOM) and the
; user must accept the ANADOCTORFADY Free Use License to install.
; The destination-location page stays enabled on purpose: there is
; deliberately NO DisableDirPage anywhere in this script.
LicenseFile=license_agreement.txt
UninstallDisplayName={#MyAppName}
; Never delete patient data on uninstall: there is deliberately NO
; UninstallDelete section in this script. %APPDATA%\ANADOCTORFADY
; (clinic.db, reports, backups, xrays, scans) is left untouched.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"

[Files]
; Only the program itself. Patient data is NOT shipped and NOT touched.
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcut (always) + Desktop shortcut (always).
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
