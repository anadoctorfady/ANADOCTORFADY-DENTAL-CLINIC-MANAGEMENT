; ANADOCTORFADY v2 - Inno Setup installer script (Windows only)
; ============================================================
; Build the program FIRST with the ONEDIR build
; (installer\build_exe_onedir.bat -> installer\dist\ANADOCTORFADY\
; folder), then compile this script with Inno Setup 6 (free,
; https://jrsoftware.org/isdl.php) or run installer\build_installer.bat,
; which finds ISCC.exe for you.
; Output: installer\output\ANADOCTORFADY_Setup.exe
; (The onefile build_exe_x86.bat / build_exe.bat stays for the portable
; single-EXE download; only this Setup ships the onedir folder - see
; the round-49 note at the [Files] section below.)
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
; The license page comes BEFORE the destination page (Inno shows
; LicenseFile before Select Destination Location by design).
LicenseFile=license_agreement.txt
; ------------------------------------------------------------------
; Round 49, Section C: the Select Destination Location page MUST
; appear on EVERY install - fresh AND upgrade - pre-filled with the
; folder the previous version was installed to.
;
; Why it did NOT appear on upgrades before (Inno Setup 6 docs,
; jrsoftware.org/ishelp/topic_setup_disabledirpage.htm):
; DisableDirPage DEFAULTS to "auto" when the directive is absent -
; it is NOT "no". With "auto", Setup looks in the registry for a
; previous installation of the same AppId, and if it finds one it
; SKIPS the Select Destination Location page entirely. So having
; no DisableDirPage line at all (the old state of this script)
; still hid the page on every upgrade install; the owner only
; ever saw it on the very first install.
;
; The fix is the pair below:
; - DisableDirPage=no: NEVER skip the page - it is always shown.
; - UsePreviousAppDir=yes (also the documented default, stated
;   explicitly here): at startup Setup reads the previous install
;   folder from the registry and uses it as the pre-filled default
;   on that page. On a fresh install there is no previous folder,
;   so the page falls back to DefaultDirName above
;   ({localappdata}\ANADOCTORFADY). The user may still Browse to
;   any other folder on either kind of install.
; Docs: topic_setup_disabledirpage.htm ("If this is set to auto,
; Setup will not show the Select Destination Location wizard page
; if it finds the directory of a previous installation") and
; topic_setup_usepreviousappdir.htm (registry lookup of the same
; application's previous directory as the wizard default).
; NOTE: {app} is only the PROGRAM folder. Patient data lives in
; %APPDATA%\ANADOCTORFADY and is never read or written by Setup,
; whichever folder the user picks here.
DisableDirPage=no
UsePreviousAppDir=yes
UninstallDisplayName={#MyAppName}
; Never delete patient data on uninstall: there is deliberately NO
; UninstallDelete section in this script. %APPDATA%\ANADOCTORFADY
; (clinic.db, reports, backups, xrays, scans) is left untouched.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"

[Files]
; Only the program itself. Patient data is NOT shipped and NOT touched.
; Round 49, Section D: ship the ONEDIR build (dist\ANADOCTORFADY\ -
; ANADOCTORFADY.exe + its DLLs/support files side by side) instead of
; the single onefile EXE. A onefile PyInstaller EXE unpacks itself to
; a temp folder on EVERY launch, which is the main avoidable part of
; the slow reopen the owner reported; the onedir layout starts in
; place with no extraction. [Icons]/[Run] below still point at
; {app}\ANADOCTORFADY.exe, which is where this entry puts it.
Source: "dist\ANADOCTORFADY\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu shortcut (always) + Desktop shortcut (always).
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
