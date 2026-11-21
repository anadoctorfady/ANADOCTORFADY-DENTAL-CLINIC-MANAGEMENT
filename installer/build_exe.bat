@echo off
chcp 65001 >nul
title ANADOCTORFADY - Build EXE
echo ================================================
echo  ANADOCTORFADY v2 - Build EXE (Windows 7/8/10/11)
echo  Build ANADOCTORFADY.exe on Windows - x86 and x64
echo ================================================
echo.
echo IMPORTANT - Python version:
echo   Windows 7 : Python 3.8.10 + PyInstaller 5.13 ONLY
echo   Windows 10/11 : Python 3.11+ + latest PyInstaller
echo   (Install Python from python.org and tick "Add Python to PATH")
echo.
echo RECOMMENDED: use 32-bit Python - the EXE then works on
echo   BOTH x86 (32-bit) AND x64 (64-bit) Windows.
echo   python.org -^> Windows installer (32-bit)
echo.
echo SEPARATE BUILDS: for one EXE per architecture, use instead:
echo   installer\build_exe_x86.bat  -^> ANADOCTORFADY_x86.exe (x86 + x64)
echo   installer\build_exe_x64.bat  -^> ANADOCTORFADY_x64.exe (x64 only)
echo   See installer\PYTHON_SIZES.md for Python sizes per environment.
echo.
python --version
if errorlevel 1 (
  echo [ERROR] Python not found!
  echo Install Python, tick "Add Python to PATH", then run this file again.
  pause
  exit /b 1
)
echo.
echo Detecting Python architecture...
python -c "import struct; print(struct.calcsize('P')*8)" > "%TEMP%\anadoctor_arch.txt"
set /p PYBITS=<"%TEMP%\anadoctor_arch.txt"
del "%TEMP%\anadoctor_arch.txt"
if "%PYBITS%"=="32" (
  echo [OK] 32-bit Python detected - the EXE will work on x86 AND x64.
  set ARCH=x86
) else if "%PYBITS%"=="64" (
  echo.
  echo [WARNING] 64-bit Python detected!
  echo   The EXE built now will run ONLY on x64 Windows.
  echo   It will NOT run on x86 Windows.
  echo.
  echo   To build a universal EXE for x86 + x64, stop now with Ctrl+C,
  echo   install 32-bit Python, and run this file again.
  echo.
  echo   Press any key to continue with an x64-only EXE, or Ctrl+C to stop.
  pause
  set ARCH=x64
) else (
  echo [WARNING] Could not detect Python architecture - got "%PYBITS%".
  echo   Continuing anyway - the EXE architecture will match this Python.
  set ARCH=unknown
)
echo Architecture: %ARCH%
echo.
cd /d %~dp0
cd ..
echo Repo folder: %CD%
if not exist requirements.txt (
  echo.
  echo [ERROR] requirements.txt not found in %CD%
  echo Extract the WHOLE zip first to a real folder like C:\ANADOCTORFADY
  echo Do not run this file from inside the zip and do not copy it alone.
  echo Then run installer\build_exe.bat from that folder.
  pause
  exit /b 1
)
echo [OK] Found requirements.txt in %CD%
echo [1/4] Creating virtual environment...
if not exist venv (
  python -m venv venv
  if errorlevel 1 (
    echo [ERROR] Could not create venv.
    pause
    exit /b 1
  )
)
call venv\Scripts\activate.bat
echo [2/4] Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] pip install failed. Check your internet connection.
  pause
  exit /b 1
)
echo.
echo [NOTE] Windows 7: installing PyInstaller 5.13 (last version for Win7)
echo        Windows 10/11: installing latest PyInstaller
ver | findstr /C:"6.1" >nul
if %errorlevel%==0 (
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
  echo Check the messages above. Common causes: wrong Python version,
  echo missing PyInstaller, or antivirus blocking PyInstaller.
  pause
  exit /b 1
)
cd ..
echo.
echo [4/4] Done!
if exist installer\dist\ANADOCTORFADY.exe (
  copy /Y installer\dist\ANADOCTORFADY.exe installer\dist\ANADOCTORFADY_%ARCH%.exe >nul
  echo SUCCESS: installer\dist\ANADOCTORFADY.exe
  echo          also saved as installer\dist\ANADOCTORFADY_%ARCH%.exe
  echo.
  echo Optional code signing - skipped unless CERT_PFX + CERT_PASS are set:
  if defined CERT_PFX if defined CERT_PASS (
    where signtool >nul 2>&1
    if not errorlevel 1 (
      signtool sign /f "%CERT_PFX%" /p "%CERT_PASS%" /tr http://timestamp.digicert.com /td sha256 /fd sha256 installer\dist\ANADOCTORFADY.exe
      if errorlevel 1 echo [WARNING] signtool failed - EXE is still usable, just unsigned.
    ) else (
      echo [NOTE] signtool not found - signing skipped. Install Windows SDK for signtool.
    )
  ) else (
    echo [NOTE] Signing skipped: CERT_PFX/CERT_PASS not set - see SECURITY.md.
  )
  echo.
  if "%ARCH%"=="x86" (
    echo This 32-bit EXE works on BOTH x86 and x64 Windows.
  ) else (
    echo This EXE is %ARCH% - it runs ONLY on %ARCH% Windows.
  )
  echo.
  echo Next steps:
  echo   1. Copy ANADOCTORFADY.exe to any folder, e.g. Desktop or C:\ANADOCTORFADY
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
