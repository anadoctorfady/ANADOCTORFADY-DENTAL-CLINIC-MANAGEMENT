# -*- mode: python ; coding: utf-8 -*-
# ANADOCTORFADY v2 - PyInstaller ONEDIR spec (Setup-path build, round 49)
# ======================================================================
# This is a copy of ANADOCTORFADY.spec switched to ONEDIR mode. It is
# the build the Inno Setup installer ships (see ANADOCTORFADY.iss
# [Files]): PyInstaller produces a dist/ANADOCTORFADY/ FOLDER holding
# ANADOCTORFADY.exe next to its DLLs and support files.
# WHY: the onefile EXE (ANADOCTORFADY.spec, kept unchanged for the
# portable single-file download) unpacks itself into a temp folder on
# EVERY launch - on the owner's PC that extraction (plus antivirus
# scanning of the freshly extracted files) is the main avoidable part
# of the slow app reopen. The onedir build starts in place: no
# extraction, nothing new for the antivirus to rescan each time.
# Build from the package root with:
#   pyinstaller installer/ANADOCTORFADY_onedir.spec --clean --noconfirm
# or simply run installer/build_exe_onedir.bat (recommended, 32-bit).
# Everything else - entry point, datas, hiddenimports, icon - is
# identical to ANADOCTORFADY.spec; only the EXE/COLLECT packaging at
# the bottom differs (exclude_binaries=True + COLLECT).
# Writable data (clinic.db, reports/, backups/, xrays/) is NOT bundled:
# it lives in the fixed per-user %APPDATA%\ANADOCTORFADY location (see
# src/config/settings.py). Do NOT ship a clinic.db inside the build.
import os

a = Analysis(
    ['../main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../assets', 'assets'),
        ('../src', 'src'),
    ],
    hiddenimports=[
        'reportlab', 'reportlab.lib', 'reportlab.pdfbase.ttfonts',
        'openpyxl', 'hijri_converter', 'hijri_converter.convert',
        'arabic_reshaper', 'bidi', 'PIL', 'PIL.Image', 'sqlite3',
        'tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ANADOCTORFADY',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Icon: resolved from installer/ dir (this file's folder), so the path
    # is ../assets/app.ico (package root assets/). Verified to exist.
    # datas above already bundle the whole assets/ folder, so the logo
    # files are also available at runtime via the _internal/assets/ folder.
    icon='../assets/app.ico' if os.path.exists('../assets/app.ico') else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ANADOCTORFADY',
)
