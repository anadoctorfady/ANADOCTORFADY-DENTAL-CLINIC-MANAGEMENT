@echo off
chcp 65001 >nul
title ANADOCTORFADY - Build ONEDIR (x86 / 32-bit, for Setup)
echo ================================================
echo  ANADOCTORFADY v2 - Build ONEDIR folder for x86 (32-bit)
echo  Output: installer\dist\ANADOCTORFADY\ (folder with the EXE)
echo  This is the build the Windows installer (Setup) ships.
echo  It starts faster than the onefile EXE: no unpacking on
echo  every launch. The onefile build_exe_x86.bat stays for the
echo  portable single-EXE download.
echo  The resulting program works on BOTH x86 and x64 Windows
echo ================================================
echo.
echo This script needs 32-bit Python. It looks for it in this order:
echo  1. C:\Python311-32\python.exe
echo  2. C:\Python38-32\python.exe  (Windows 7)
echo  3. py -3.11-32   (Python launcher)
echo  4. py -3.8-32    (Python launcher, Windows 7)
echo  5. python        (from PATH - must be 32-bit, checked below)
echo.
cd /d %~dp0
cd ..
echo Repo folder: %CD%
if not exist requirements.txt (
  echo.
  echo [ERROR] requirements.txt not found in %CD%
  echo Extract the WHOLE zip first to a real folder like C:\ANADOCTORFADY
  echo Do not run this file from inside the zip and do not copy it alone.
  echo Then run installer\build_exe_onedir.bat from that folder.
  pause
  exit /b 1
)
echo [OK] Found requirements.txt in %CD%
set "PY="
if exist "C:\Python311-32\python.exe" set "PY=C:\Python311-32\python.exe"
if not defined PY if exist "C:\Python38-32\python.exe" set "PY=C:\Python38-32\python.exe"
if not defined PY (
  py -3.11-32 --version >nul 2>&1
  if not errorlevel 1 set "PY=py -3.11-32"
)
if not defined PY (
  py -3.8-32 --version >nul 2>&1
  if not errorlevel 1 set "PY=py -3.8-32"
)
if not defined PY (
  python --version >nul 2>&1
  if not errorlevel 1 set "PY=python"
)
if not defined PY (
  echo [ERROR] No Python found!
  echo Install 32-bit Python first - see installer\PYTHON_SIZES.md
  pause
  exit /b 1
)
echo Using Python: %PY%
%PY% --version
%PY% -c "import struct; print(struct.calcsize('P')*8)" > "%TEMP%\anadoctor_arch.txt"
set /p PYBITS=<"%TEMP%\anadoctor_arch.txt"
del "%TEMP%\anadoctor_arch.txt"
if not "%PYBITS%"=="32" (
  echo.
  echo [ERROR] This script needs 32-bit Python, but found %PYBITS%-bit Python.
  echo   Install 32-bit Python - see installer\PYTHON_SIZES.md - or run
  echo   build_exe_x64.bat instead for a 64-bit-only build.
  pause
  exit /b 1
)
echo [OK] 32-bit Python confirmed (32).
%PY% -c "import sys; print(str(sys.version_info[0])+'.'+str(sys.version_info[1]))" > "%TEMP%\anadoctor_ver.txt"
set /p PYVER=<"%TEMP%\anadoctor_ver.txt"
del "%TEMP%\anadoctor_ver.txt"
echo Python version: %PYVER%
if "%PYVER%"=="3.8" (
  echo [NOTE] Python 3.8 - using PyInstaller 5.13, last version for Windows 7.
) else (
  echo [NOTE] Python %PYVER% - using latest PyInstaller.
)
echo.
echo [1/4] Creating virtual environment .venv-x86...
if not exist .venv-x86 (
  %PY% -m venv .venv-x86
  if errorlevel 1 (
    echo [ERROR] Could not create venv.
    pause
    exit /b 1
  )
)
call .venv-x86\Scripts\activate.bat
echo [2/4] Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] pip install failed. Check your internet connection.
  pause
  exit /b 1
)
if "%PYVER%"=="3.8" (
  pip install "pyinstaller==5.13"
) else (
  pip install pyinstaller
)
if errorlevel 1 (
  echo [ERROR] PyInstaller install failed.
  pause
  exit /b 1
)
echo [3/4] Building ONEDIR folder (2-4 minutes, please wait)...
cd installer
pyinstaller --noconfirm --clean ANADOCTORFADY_onedir.spec
if errorlevel 1 (
  echo.
  echo [ERROR] Build failed.
  pause
  exit /b 1
)
cd ..
echo.
echo [4/4] Done!
if exist installer\dist\ANADOCTORFADY\ANADOCTORFADY.exe (
  echo SUCCESS: installer\dist\ANADOCTORFADY\ANADOCTORFADY.exe
  echo.
  echo Optional code signing - skipped unless CERT_PFX + CERT_PASS are set:
  if defined CERT_PFX if defined CERT_PASS (
    where signtool >nul 2>&1
    if not errorlevel 1 (
      signtool sign /f "%CERT_PFX%" /p "%CERT_PASS%" /tr http://timestamp.digicert.com /td sha256 /fd sha256 installer\dist\ANADOCTORFADY\ANADOCTORFADY.exe
      if errorlevel 1 echo [WARNING] signtool failed - program is still usable, just unsigned.
    ) else (
      echo [NOTE] signtool not found - signing skipped. Install Windows SDK for signtool.
    )
  ) else (
    echo [NOTE] Signing skipped: CERT_PFX/CERT_PASS not set - see SECURITY.md.
  )
  echo.
  echo This 32-bit build works on BOTH x86 and x64 Windows.
  echo Keep the WHOLE installer\dist\ANADOCTORFADY folder together -
  echo the EXE needs the files next to it. Do not copy the EXE alone.
  echo.
  echo Next steps:
  echo   1. Build the installer: run installer\build_installer.bat
  echo      It packs this folder into ANADOCTORFADY_Setup.exe.
  echo   2. Or test now: double-click
  echo      installer\dist\ANADOCTORFADY\ANADOCTORFADY.exe
  echo      First run creates the data folder
  echo      %APPDATA%\ANADOCTORFADY with clinic.db and reports.
  echo   3. Login:  fady  /  1234
  echo   4. End users need NOTHING else: no Python, no Office, no internet.
) else (
  echo [ERROR] ANADOCTORFADY.exe not found inside installer\dist\ANADOCTORFADY after build.
  pause
  exit /b 1
)
echo.
pause
