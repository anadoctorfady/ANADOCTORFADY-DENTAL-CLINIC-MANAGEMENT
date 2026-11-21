@echo off
chcp 65001 >nul
title ANADOCTORFADY - Build Windows Installer
echo ================================================
echo  ANADOCTORFADY v2 - Build the Windows installer
echo  Build the installer - Inno Setup - Windows only
echo ================================================
echo.
cd /d %~dp0
cd ..
echo Repo folder: %CD%
if not exist installer\dist\ANADOCTORFADY.exe (
  if exist installer\dist\ANADOCTORFADY_x86.exe (
    echo [INFO] Found installer\dist\ANADOCTORFADY_x86.exe but not ANADOCTORFADY.exe.
    echo The x86 build IS the app EXE - copying it to ANADOCTORFADY.exe now...
    copy /Y installer\dist\ANADOCTORFADY_x86.exe installer\dist\ANADOCTORFADY.exe >nul
    if exist installer\dist\ANADOCTORFADY.exe echo [OK] Copied. Continuing with the installer build.
  )
)
if not exist installer\dist\ANADOCTORFADY.exe (
  echo [ERROR] EXE file not found.
  echo Checked this exact path:
  echo   %CD%\installer\dist\ANADOCTORFADY.exe
  echo.
  echo What is actually inside installer\dist right now:
  if exist installer\dist dir /b installer\dist
  if not exist installer\dist echo   The installer\dist folder does not exist.
  echo.
  echo Build the EXE FIRST:
  echo   installer\build_exe.bat
  echo   Recommended: installer\build_exe_x86.bat - it works on x86 and x64.
  echo Then run this file again.
  echo.
  echo If you DID build the EXE and it is gone now, Windows Security
  echo may have quarantined it. Open Windows Security, then go to
  echo Virus and threat protection, then Protection history, and
  echo look for ANADOCTORFADY.exe. If it is listed there, restore
  echo it, and add a folder exclusion for this repo folder:
  echo   %CD%
  echo under Virus and threat protection settings, Exclusions.
  echo.
  echo [ERROR] EXE file not found - build the EXE first, then try again.
  pause
  exit /b 1
)
echo [1/2] Looking for Inno Setup compiler - ISCC.exe...
set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles(x86)%\Inno Setup 5\ISCC.exe" set ISCC="%ProgramFiles(x86)%\Inno Setup 5\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 5\ISCC.exe" set ISCC="%ProgramFiles%\Inno Setup 5\ISCC.exe"
if not defined ISCC (
  where ISCC.exe >nul 2>&1
  if not errorlevel 1 set ISCC=ISCC.exe
)
if not defined ISCC (
  echo.
  echo [ERROR] Inno Setup is not installed on this computer.
  echo Inno Setup is FREE. Download and install it from:
  echo   https://jrsoftware.org/isdl.php
  echo Download innosetup-6.x.x.exe, run it, accept the defaults,
  echo then run this file again.
  echo.
  echo [ERROR] Inno Setup is not installed - download it free from the link above.
  pause
  exit /b 1
)
echo [OK] Found Inno Setup: %ISCC%
echo.
echo Checking for a stale installer\output\ANADOCTORFADY_Setup.exe ...
if exist installer\output\ANADOCTORFADY_Setup.exe (
  del /F installer\output\ANADOCTORFADY_Setup.exe >nul 2>&1
  if exist installer\output\ANADOCTORFADY_Setup.exe (
    echo [WARNING] Could not delete the old installer\output\ANADOCTORFADY_Setup.exe - it is locked.
    echo   Close the installer/app, end ANADOCTORFADY_Setup.exe in Task Manager,
    echo   and delete installer\output\ANADOCTORFADY_Setup.exe manually, then retry.
  ) else (
    echo [OK] Removed the old installer\output\ANADOCTORFADY_Setup.exe.
  )
)
echo [2/2] Compiling installer\ANADOCTORFADY.iss ...
%ISCC% installer\ANADOCTORFADY.iss
if errorlevel 1 (
  echo.
  echo [ERROR] Installer build failed - see the messages above.
  echo If the error mentions EndUpdateResource or a locked file:
  echo   Close the installer/app, end ANADOCTORFADY_Setup.exe in Task Manager,
  echo   delete installer\output\ANADOCTORFADY_Setup.exe manually, then retry.
  echo   If it still fails, pause antivirus for this folder or restart the PC.
  pause
  exit /b 1
)
echo.
echo SUCCESS: installer\output\ANADOCTORFADY_Setup.exe
echo.
echo What the installer does:
echo   - Installs the program to %%LOCALAPPDATA%%\ANADOCTORFADY
echo   - Creates Desktop + Start Menu shortcuts
echo   - Patient data stays in %%APPDATA%%\ANADOCTORFADY and is NEVER
echo     touched by install, upgrade, reinstall or uninstall.
echo   - First run migrates an old next-to-EXE database automatically.
echo.
echo Next step: double-click installer\output\ANADOCTORFADY_Setup.exe
echo Login:  fady  /  1234
echo.
pause
