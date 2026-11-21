@echo off
chcp 65001 >nul
title ANADOCTORFADY - Obfuscated Build (optional)
echo ================================================
echo  ANADOCTORFADY v2 - Obfuscated Build (PyArmor, optional)
echo ================================================
echo.
echo This is OPTIONAL. Without PyArmor it falls back to the normal
echo build (installer\build_exe.bat). Obfuscation makes reverse
echo engineering HARDER, it does NOT make it impossible - see SECURITY.md.
echo.
cd /d %~dp0
cd ..
pyarmor --version >nul 2>&1
if errorlevel 1 (
  echo [WARNING] PyArmor is NOT installed - falling back to the normal build.
  echo   To use obfuscation:  pip install pyarmor
  echo   PyArmor 8 basic edition is free; advanced features are paid.
  call installer\build_exe.bat
  exit /b %errorlevel%
)
echo [OK] PyArmor found. Obfuscating main.py + the whole src tree...
echo     (pyarmor gen -O obfuscated -r main.py src)
if exist obfuscated rmdir /S /Q obfuscated
pyarmor gen -O obfuscated -r main.py src
if errorlevel 1 (
  echo [WARNING] PyArmor obfuscation failed - falling back to the normal build.
  call installer\build_exe.bat
  exit /b %errorlevel%
)
echo [OK] Obfuscated code is in obfuscated\ (do NOT edit it - it is generated).
echo.
echo [INFO] Building the EXE from the obfuscated code with PyInstaller...
echo   NOTE: only src\data\*.json are bundled as data here - the plain
echo   .py sources are NOT bundled, otherwise obfuscation would be pointless.
cd installer
pyinstaller --noconfirm --clean --onefile --windowed --name ANADOCTORFADY ^
  --icon ..\assets\app.ico ^
  --add-data "..\assets;assets" ^
  --add-data "..\src\data;src/data" ^
  --hidden-import reportlab --hidden-import openpyxl ^
  --hidden-import hijri_converter --hidden-import arabic_reshaper ^
  --hidden-import bidi --hidden-import PIL ^
  ..\obfuscated\main.py
if errorlevel 1 (
  echo.
  echo [WARNING] Obfuscated build failed - falling back to the normal build.
  cd ..
  call installer\build_exe.bat
  exit /b %errorlevel%
)
cd ..
echo.
if exist installer\dist\ANADOCTORFADY.exe (
  echo SUCCESS: installer\dist\ANADOCTORFADY.exe - obfuscated build
  echo.
  echo Optional code signing: set CERT_PFX + CERT_PASS env vars, else skipped.
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
) else (
  echo [ERROR] EXE not found after build.
  pause
  exit /b 1
)
echo.
pause
