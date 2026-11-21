# -*- mode: python ; coding: utf-8 -*-
# ANADOCTORFADY v2 - PyInstaller spec (Windows 7/8/10/11)
# Build from the package root with:  pyinstaller installer/ANADOCTORFADY.spec --clean --noconfirm
# or simply run installer/build_exe.bat (recommended).
# This file lives in installer/, so all paths are relative to it (.. = package root).
# Datas bundled (verified to exist in v2):
#   assets/logo.jpg + logo.png (clinic logo, shown in login + top bar)
#   assets/app.ico (Windows icon: EXE + Desktop shortcut)
#   assets/fonts/NotoNaskhArabic-Regular.ttf + -Bold.ttf  -> assets/fonts  (Arabic PDF/UI)
#   src/data/currencies.json   (178 currencies)          -> src/data
#   src/data/countries.json    (249 countries)           -> src/data
#   src/data/medications.json  (311 drugs, all classes)  -> src/data
#   src/data/interactions.json (129 interaction pairs)   -> src/data
#   src/data/phrases_seed.json (105 reusable phrases)    -> src/data
#   src/ (whole package, includes the JSONs above)       -> src
# Writable data (clinic.db, reports/, backups/, xrays/) is NOT bundled:
# it is created next to the EXE on first run (see src/config/settings.py
# frozen-aware BASE). Do NOT ship a clinic.db inside the EXE.
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
    a.binaries,
    a.datas,
    [],
    name='ANADOCTORFADY',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Icon: resolved from installer/ dir (this file's folder), so the path
    # is ../assets/app.ico (package root assets/). Verified to exist.
    # datas above already bundle the whole assets/ folder, so the logo
    # files are also available at runtime via sys._MEIPASS/assets/.
    icon='../assets/app.ico' if os.path.exists('../assets/app.ico') else None,
)
