# ANADOCTORFADY v2 — Build the EXE on Windows
# بناء ملف ANADOCTORFADY.exe على ويندوز

> ⚠️ **No EXE is included in this zip.** The EXE must be built once on a
> Windows computer with the steps below (it cannot be built on Linux/Mac).
> لا يوجد ملف EXE جاهز داخل الحزمة — يجب بناؤه مرة واحدة على ويندوز.

## Requirements / المتطلبات

| Windows | Python | PyInstaller |
|---|---|---|
| Windows 7 | **3.8.10** (only) | **5.13** (only) |
| Windows 8 / 8.1 | 3.8.10 – 3.11 | 5.13 – 6.x |
| Windows 10 / 11 | **3.11.9** (recommended; last 3.11 with a Windows installer — 3.11.10+ are source-only security updates) | latest |

- Download Python from **https://www.python.org/downloads/windows/**
- During install, tick **☑ Add Python to PATH** (important!)
- Internet needed **only for the one-time build** (to download libraries).
  The finished EXE works **offline**.

## x86 (32-bit) vs x64 (64-bit) / هل يعمل على x86 و x64؟

**Short answer: yes — if you build with 32-bit Python. / الجواب المختصر: نعم، إذا بنيت ببايثون 32-بت.**

The Python source code and SQLite database work on both. But a PyInstaller
EXE is architecture-specific: it only runs on the same architecture as the
Python that built it. So which Python you install decides which Windows
the EXE runs on:

| Build with | EXE runs on | Recommendation |
|---|---|---|
| **32-bit Python (recommended ✅)** | **x86 (32-bit) AND x64 (64-bit)** Windows | **Use this one** — a single EXE for every PC |
| 64-bit Python | **x64 (64-bit) only** — will NOT run on x86 | Only if you need >4 GB of memory (this app uses ~21 MB, so you don't) |

- On python.org, pick **"Windows installer (32-bit)"** for the universal build.
  (The 64-bit installer is labelled "Windows installer (64-bit)".)
- `build_exe.bat` detects the Python architecture at the start and prints it.
  If it finds 64-bit Python, it warns you and asks whether to continue with
  an x64-only EXE or stop and install 32-bit Python instead.
- The built file is saved as `ANADOCTORFADY.exe` **and** as
  `ANADOCTORFADY_x86.exe` (32-bit build) or `ANADOCTORFADY_x64.exe`
  (64-bit build), so the architecture is obvious from the file name.

| البناء بـ | يعمل على | التوصية |
|---|---|---|
| **بايثون 32-بت (الموصى به ✅)** | **ويندوز 32-بت و 64-بت معاً** | **استخدم هذا** — نسخة واحدة لكل الأجهزة |
| بايثون 64-بت | **64-بت فقط** — لن يعمل على 32-بت | لا حاجة له (التطبيق يستهلك ~21 ميغابايت فقط) |

## Separate builds per environment / بناء نسخة منفصلة لكل بيئة

Yes — one EXE per architecture, with its own script:

| Script | Needs | Output |
|---|---|---|
| `installer\build_exe_x86.bat` | 32-bit Python | `installer\dist\ANADOCTORFADY_x86.exe` — works on **x86 + x64** |
| `installer\build_exe_x64.bat` | 64-bit Python | `installer\dist\ANADOCTORFADY_x64.exe` — **x64 only** |

- Each script looks for its Python in order: `C:\Python311-32` (or `-64`) →
  `C:\Python38-32` (or `-64`, Windows 7) → `py -3.11-32` / `-64` →
  `py -3.8-32` / `-64` → `python` on PATH — and **verifies the bitness,
  aborting with a clear message** if the wrong one is found, instead of
  silently building the wrong EXE.
- Each build uses its own venv (`.venv-x86` / `.venv-x64`), so the two
  builds never mix.
- `installer\build_exe.bat` (the original) still works as the auto-detect
  wrapper: it uses whichever Python is on PATH and warns if it is 64-bit.
- **Python sizes per environment** (download / installed / which installer):
  see `installer\PYTHON_SIZES.md` — e.g. Python 3.8.10 installer ~27 MB
  (32-bit) / ~26.5 MB (64-bit), ~130 MB installed; Python 3.11 installer
  ~25 MB, ~150 MB installed. The built EXE itself is ~15–25 MB either way,
  and end users need **no Python at all**.

نعم — نسخة EXE منفصلة لكل بيئة، ولكل منها سكربت خاص. راجع
`installer\PYTHON_SIZES.md` لجدول أحجام بايثون لكل بيئة.

## Build steps / خطوات البناء

1. **Unzip** this package on the Windows computer, e.g. to `C:\ANADOCTORFADY`
   فك الضغط في مجلد، مثلاً `C:\ANADOCTORFADY`
2. **Right-click `installer\build_exe.bat` → Run as administrator**
   كليك يمين على `installer\build_exe.bat` ← تشغيل كمسؤول
3. Wait **2–4 minutes**. The script creates a venv, installs the 6 libraries
   (`requirements.txt`), installs PyInstaller, then builds the EXE.
   انتظر 2–4 دقائق حتى ينتهي البناء.
4. The EXE is ready at:
   **`installer\dist\ANADOCTORFADY.exe`**
   (also saved as `ANADOCTORFADY_x86.exe` for a 32-bit build or
   `ANADOCTORFADY_x64.exe` for a 64-bit build — see "x86 vs x64" above)
5. Copy `ANADOCTORFADY.exe` anywhere you like (Desktop, `C:\ANADOCTORFADY`,
   USB stick) and **double-click it**.
6. **Desktop shortcut (with the clinic logo icon):** PyInstaller one-file
   cannot create shortcuts itself, so do one of these:
   - Right-click `ANADOCTORFADY.exe` → **Send to → Desktop (create shortcut)**, or
   - Double-click **`installer\create_shortcut.vbs`** (creates
     `ANADOCTORFADY.lnk` on the Desktop, icon = `assets\app.ico`).
   The shortcut carries the gold-tooth logo icon, same as the EXE itself.

## Real Windows installer (recommended) / المثبّت الرسمي لويندوز ✅

Instead of copying the EXE by hand, build a proper installer:

1. Build the EXE first: run `installer\build_exe.bat` (see above).
2. Run **`installer\build_installer.bat`** — it finds Inno Setup
   (`ISCC.exe`) and compiles `installer\ANADOCTORFADY.iss`.
   If Inno Setup is not installed, it prints the free download link:
   **https://jrsoftware.org/isdl.php** — install it, then run the
   `.bat` again.
3. The installer is ready at **`installer\output\ANADOCTORFADY_Setup.exe`**.
4. Double-click it on any clinic PC. It installs the program to
   **`%LOCALAPPDATA%\ANADOCTORFADY`** and creates **Desktop + Start
   Menu shortcuts** automatically. No administrator rights needed.
5. Login: `fady` / `1234`.

**Your data is safe with the installer / بياناتك آمنة:**
- Patient data lives in **`%APPDATA%\ANADOCTORFADY`**
  (`C:\Users\<name>\AppData\Roaming\ANADOCTORFADY`) — a *different*
  folder from the program. The installer never installs, overwrites
  or deletes anything there.
- **Upgrade / reinstall:** only the EXE is replaced. Data untouched.
- **Uninstall:** removes only the program folder. Patient data is
  **never deleted** on uninstall — it stays in `%APPDATA%` so you can
  reinstall later and find everything still there.
- **Moving the EXE can no longer lose data:** the data location does
  not depend on where the EXE sits. If an old database is still next
  to an old EXE (on the Desktop, in Downloads, or next to the EXE),
  the first run of the new version moves it automatically into
  `%APPDATA%\ANADOCTORFADY` — the old copy is only set aside after
  the new copy is verified, never deleted.

> ⚠️ The installer itself can only be compiled on Windows (Inno Setup
> is Windows-only). On Linux you can only check the `.iss` text.

## Desktop shortcut / اختصار سطح المكتب

The installer creates the Desktop shortcut for you (see above). If you
installed by copying the EXE by hand instead, do one of these:

See step 6 above. The EXE icon and the shortcut icon are both the clinic
logo (`assets\app.ico`, gold tooth with crown on black). If you move the
EXE, the shortcut still works as long as it points at the new location —
re-run `create_shortcut.vbs` after moving it, or right-click → Send to Desktop.

## First-run SmartScreen warning / تحذير SmartScreen عند أول تشغيل

Without a paid code-signing certificate, Windows SmartScreen **will** show
"Windows protected your PC / Unknown publisher" the first time the EXE runs.
This is **not** an error or a virus warning — it means Windows does not know
the publisher. Click **"More info" → "Run anyway"** and the app runs normally.
To remove the warning permanently, buy an OV certificate (~$200–400/year)
or EV certificate and sign the EXE — see `SECURITY.md` (and the optional
`CERT_PFX`/`CERT_PASS` signing step in the build scripts).

## Optional: obfuscation + code signing / اختياري: تشويش وتوقيع

- **Obfuscation:** `installer\build_obfuscated.bat` runs PyArmor
  (`pyarmor gen -O obfuscated -r main.py src`) if PyArmor is installed,
  then builds from the obfuscated code; otherwise it falls back to the
  normal build with a warning. This makes reverse engineering harder,
  **not impossible** — see `SECURITY.md`. Do **not** use PyInstaller
  `--key` (deprecated/removed).
- **Code signing:** if `CERT_PFX` (path to `.pfx`) and `CERT_PASS` are set
  as environment variables before running a build script, the EXE is
  signed with `signtool`; otherwise signing is skipped with a note and the
  build still succeeds. Never put the `.pfx` or its password in the zip.

## First run / أول تشغيل

- Login: username **`fady`** — password **`1234`** (changeable in Settings).
- First run automatically creates your per-user data folder:
  - Windows: **`%APPDATA%\ANADOCTORFADY\clinic.db`** — the database
    (patients, visits, prescriptions…)
  - `%APPDATA%\ANADOCTORFADY\reports\` — patient PDFs + prescription PDFs
  - `%APPDATA%\ANADOCTORFADY\backups\`, `\xrays\`, `\scans\`
- The data folder does **not** depend on where the EXE sits: you can
  move the EXE (or the Desktop shortcut) anywhere and your data stays
  in `%APPDATA%\ANADOCTORFADY`. If an old database is still next to an
  old EXE, the first run moves it there automatically (verified copy;
  the old file is kept as `clinic.db.migrated-<date>.bak`, never deleted).
- **End users need nothing else**: no Python, no Office, no internet.
  المستخدم النهائي لا يحتاج تثبيت أي شيء آخر.

## What is inside the EXE / ماذا يحتوي

- Warm Sand light + Warm Charcoal dark mode, bilingual EN/AR
- 178 currencies, 249 countries/nationalities, 315 drugs (all classes),
  129 drug-interaction pairs, 105 reusable phrases
- Arabic fonts (Noto Naskh Arabic) bundled — Arabic renders joined, RTL,
  in the UI and in PDFs.

## Troubleshooting / حل المشاكل

| Problem | Fix |
|---|---|
| `Python not found` | Reinstall Python and tick **Add Python to PATH**, then reopen the terminal |
| Build fails on Windows 7 | Use **Python 3.8.10** and **PyInstaller 5.13** only (newer versions do not support Win7) |
| `pip install` fails | Check internet; try `pip install -r requirements.txt` manually in a terminal |
| Antivirus blocks / deletes the EXE | False positive (common for PyInstaller apps). Add the folder to the antivirus exclusions, rebuild, or restore from quarantine |
| SmartScreen: "Windows protected your PC / Unknown publisher" | Not an error — no code-signing certificate yet. Click "More info → Run anyway". To remove it, buy an OV/EV certificate and sign (see `SECURITY.md`) |
| Arabic letters disconnected in PDF | The Noto fonts are bundled (`assets/fonts`). If a PDF still shows disconnected letters, rebuild — do not delete the `assets` folder before building |
| EXE starts but data is gone after restart | Fixed in v2 (Item 3): data now lives in the fixed per-user folder `%APPDATA%\ANADOCTORFADY`, not next to the EXE — moving the EXE can no longer lose data. An old database next to an old EXE is migrated automatically on first run (looked for next to the EXE, on the Desktop, and in Downloads). If your old data was somewhere else, copy the old `anadoctorfady\clinic.db` into `%APPDATA%\ANADOCTORFADY\` before the first run |
| `MSVCP140.dll missing` | Install Microsoft Visual C++ Redistributable **matching your build**: x86 version for a 32-bit EXE, x64 version for a 64-bit EXE (microsoft.com) |
| EXE won't start on a 32-bit PC | It was built with 64-bit Python (x64-only). Rebuild with **32-bit Python** — see "x86 vs x64" above |
| Slow first start (a few seconds) | Normal for a one-file EXE: it extracts to a temp folder once per start |

## Rebuilding after an update / إعادة البناء بعد تحديث

1. Replace the changed `.py` / `.json` files in the package folder.
2. Run `python run_tests.py` — it must print **44/44 test files passed**.
3. Run `installer\build_exe.bat` again — it overwrites `dist\ANADOCTORFADY.exe`.
4. Run `installer\build_installer.bat` to rebuild
   `installer\output\ANADOCTORFADY_Setup.exe`, then install it on the
   clinic PC — it only replaces the EXE; patient data in
   `%APPDATA%\ANADOCTORFADY` is never touched.
   **Do NOT overwrite `%APPDATA%\ANADOCTORFADY\clinic.db` or
   `%APPDATA%\ANADOCTORFADY\reports\`** — install the new version
   over the old one only.
   See also `UPDATE_GUIDE.md` in the package root.
