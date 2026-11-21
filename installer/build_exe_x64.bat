@echo off
chcp 65001 >nul
title ANADOCTORFADY - Build EXE (x64 / 64-bit)
echo ================================================
echo  ANADOCTORFADY v2 - Build EXE for x64 (64-bit)
echo  The resulting EXE works ONLY on x64 (64-bit) Windows
echo ================================================
echo.
echo This script needs 64-bit Python. It looks for it in this order:
echo  1. C:\Python311-64\python.exe
echo  2. C:\Python38-64\python.exe  (Windows 7)
echo  3. py -3.11-64   (Python launcher)
echo  4. py -3.8-64    (Python launcher, Windows 7)
echo  5. python        (from PATH - must be 64-bit, checked below)
echo.
echo TIP: if you want ONE EXE that works on both x86 and x64 Windows,
echo   use build_exe_x86.bat instead (32-bit build).
echo.
cd /d %~dp0
cd ..
echo Repo folder: %CD%
if not exist requirements.txt (
  echo.
  echo [ERROR] requirements.txt not found in %CD%
  echo Extract the WHOLE zip first to a real folder like C:\ANADOCTORFADY
  echo Do not run this file from inside the zip and do not copy it alone.
  echo Then run installer\build_exe_x64.bat from that folder.
  pause
  exit /b 1
)
echo [OK] Found requirements.txt in %CD%
set "PY="
if exist "C:\Python311-64\python.exe" set "PY=C:\Python311-64\python.exe"
if not defined PY if exist "C:\Python38-64\python.exe" set "PY=C:\Python38-64\python.exe"
if not defined PY (
  py -3.11-64 --version >nul 2>&1
  if not errorlevel 1 set "PY=py -3.11-64"
)
if not defined PY (
  py -3.8-64 --version >nul 2>&1
  if not errorlevel 1 set "PY=py -3.8-64"
)
if not defined PY (
  python --version >nul 2>&1
  if not errorlevel 1 set "PY=python"
)
if not defined PY (
  echo [ERROR] No Python found!
  echo Install 64-bit Python first - see installer\PYTHON_SIZES.md
  pause
  exit /b 1
)
echo Using Python: %PY%
%PY% --version
%PY% -c "import struct; print(struct.calcsize('P')*8)" > "%TEMP%\anadoctor_arch.txt"
set /p PYBITS=<"%TEMP%\anadoctor_arch.txt"
del "%TEMP%\anadoctor_arch.txt"
if not "%PYBITS%"=="64" (
  echo.
  echo [ERROR] This script needs 64-bit Python, but found %PYBITS%-bit Python.
  echo   Install 64-bit Python - see installer\PYTHON_SIZES.md - or run
  echo   build_exe_x86.bat instead for an EXE that works on both x86 and x64.
  pause
  exit /b 1
)
echo [OK] 64-bit Python confirmed (64).
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
echo [1/4] Creating virtual environment .venv-x64...
if not exist .venv-x64 (
  %PY% -m venv .venv-x64
  if errorlevel 1 (
    echo [ERROR] Could not create venv.
    pause
    exit /b 1
  )
)
call .venv-x64\Scripts\activate.bat
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
echo [3/4] Building EXE (2-4 minutes, please wait)...
cd installer
pyinstaller --noconfirm --clean ANADOCTORFADY.spec
if errorlevel 1 (
  echo.
  echo [ERROR] Build failed.
  pause
  exit /b 1
)
cd ..
echo.
echo [4/4] Done!
if exist installer\dist\ANADOCTORFADY.exe (
  copy /Y installer\dist\ANADOCTORFADY.exe installer\dist\ANADOCTORFADY_x64.exe >nul
  echo SUCCESS: installer\dist\ANADOCTORFADY_x64.exe
  echo.
  echo Optional code signing - skipped unless CERT_PFX + CERT_PASS are set:
  if defined CERT_PFX if defined CERT_PASS (
    where signtool >nul 2>&1
    if not errorlevel 1 (
      signtool sign /f "%CERT_PFX%" /p "%CERT_PASS%" /tr http://timestamp.digicert.com /td sha256 /fd sha256 installer\dist\ANADOCTORFADY_x64.exe
      if errorlevel 1 echo [WARNING] signtool failed - EXE is still usable, just unsigned.
    ) else (
      echo [NOTE] signtool not found - signing skipped. Install Windows SDK for signtool.
    )
  ) else (
    echo [NOTE] Signing skipped: CERT_PFX/CERT_PASS not set - see SECURITY.md.
  )
  echo.
  echo This 64-bit EXE works ONLY on x64 Windows.
  echo.
  echo Next steps:
  echo   1. Copy ANADOCTORFADY_x64.exe anywhere - Desktop, C:\ANADOCTORFADY, USB
  echo   2. Double-click it. First run creates the data folder
  echo      %APPDATA%\ANADOCTORFADY with clinic.db and reports.
  echo   3. Login:  fady  /  1234
  echo   4. End users need NOTHING else: no Python, no Office, no internet.
) else (
  echo [ERROR] EXE not found after build.
  pause
  exit /b 1
)
echo.
pause
