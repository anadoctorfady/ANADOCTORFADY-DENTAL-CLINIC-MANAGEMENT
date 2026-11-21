# Python sizes per environment — أحجام بايثون لكل بيئة

> PyInstaller cannot cross-compile: a 64-bit Python builds a Win64 EXE,
> a 32-bit Python builds a Win32 EXE. So one Python install = one EXE
> architecture. To build **both**, install **both** Pythons side by side —
> they do not conflict when they live in different folders.
>
> لا يمكن لـ PyInstaller البناء المتبادل بين المعماريتين: بايثون 64-بت يبني
> EXE لويندوز 64-بت، وبايثون 32-بت يبني EXE لويندوز 32-بت. لبناء الاثنين،
> ثبّت نسختي بايثون جنباً إلى جنب — لا تتعارضان إذا كانتا في مجلدين مختلفين.

## Size table / جدول الأحجام

| Environment / البيئة | Python | Installer file / ملف التثبيت | Download / التنزيل | Installed / بعد التثبيت * | PyInstaller | Build script | Output EXE |
|---|---|---|---|---|---|---|---|
| Win7 SP1 **x86** | **3.8.10** 32-bit | `python-3.8.10.exe` (32-bit) | ~**27 MB** | ~**130 MB** | 5.13 | `build_exe_x86.bat` | `ANADOCTORFADY_x86.exe` — works on Win7/8/10/11 **x86 + x64** |
| Win7 SP1 **x64** | **3.8.10** 64-bit | `python-3.8.10-amd64.exe` | ~**26.5 MB** | ~**130 MB** | 5.13 | `build_exe_x64.bat` | `ANADOCTORFADY_x64.exe` — **x64 only** |
| Win10/11 **x86** | **3.11** 32-bit | `python-3.11.9.exe` (32-bit) | **23.8 MB** | ~**150 MB** | latest | `build_exe_x86.bat` | `ANADOCTORFADY_x86.exe` — works on Win7/8/10/11 **x86 + x64** |
| Win10/11 **x64** | **3.11** 64-bit | `python-3.11.9-amd64.exe` | **25.0 MB** | ~**150 MB** | latest | `build_exe_x64.bat` | `ANADOCTORFADY_x64.exe` — **x64 only** |

\* Installed size is approximate: the base Python install plus a venv with
the 6 project libraries (~80 MB extra in the venv). It varies with the pip
cache and the exact 3.11.x patch release. Download sizes are the installer
files from python.org. **Note (2026-11-08): 3.11.9 is the last 3.11 release with binary installers; 3.11.10 and later are source-only security updates (no .exe).**

**The built EXE itself is ~15–25 MB** (one-file: Python + libraries + Arabic
fonts bundled inside). It is the same size for x86 and x64.

**End users need NO Python at all** — only the builder installs Python once.
The finished EXE is a single double-click file with everything inside.
المستخدم النهائي لا يحتاج بايثون أبداً — فقط من يبني الـ EXE يثبّته مرة واحدة.

## Why Python 3.8.10 for Windows 7? / لماذا 3.8.10 لويندوز 7؟

Python 3.8.10 is the **last official Python for Windows 7 SP1** (Python 3.9+
requires Windows 10+). PyInstaller 5.13 is the last version that supports
Windows 7. The build scripts detect Python 3.8 automatically and pin
PyInstaller 5.13 for it.
بايثون 3.8.10 هو **آخر إصدار رسمي يدعم ويندوز 7** (3.9 فأعلى يحتاج ويندوز 10+).

## Best way to install both (side by side) / أفضل طريقة لتثبيت الاثنين معاً

1. **Install 64-bit first** — download from
   https://www.python.org/downloads/windows/ , tick
   **☑ Add Python to PATH**, install to the default folder
   (e.g. `C:\Python311-64` — rename it during install, or accept the
   default `C:\Users\<you>\AppData\Local\Programs\Python\Python311`).
   ثبّت نسخة 64-بت أولاً وعلّم "Add Python to PATH".
2. **Install 32-bit second, to a custom folder** — run the 32-bit installer,
   choose **Customize installation**, set the folder to
   `C:\Python311-32` (or `C:\Python38-32` for Windows 7), and
   **do NOT tick "Add Python to PATH"** for this second install.
   The `py` launcher (installed with the first Python) is how you pick
   between them — no PATH conflict.
   ثبّت نسخة 32-بت ثانياً في مجلد مخصص، **بدون** إضافة PATH، واستخدم
   مشغّل `py` للاختيار بينهما.
3. **Verify** which is which / تحقق:
   ```
   py -3.11-32 -c "import struct; print(struct.calcsize('P')*8)"
   → 4   (32-bit)
   py -3.11-64 -c "import struct; print(struct.calcsize('P')*8)"
   → 8   (64-bit)
   ```
   (For Windows 7 use `-3.8-32` / `-3.8-64` instead of `-3.11-32` / `-3.11-64`.)
4. **Build each EXE with its own script** — each script finds its Python
   automatically (`C:\Python311-32` → `C:\Python38-32` → `py -3.11-32` →
   `py -3.8-32` → `python` on PATH, verifying the bitness), creates its own
   venv (`.venv-x86` / `.venv-x64`), and writes its own output
   (`dist\ANADOCTORFADY_x86.exe` / `dist\ANADOCTORFADY_x64.exe`).
   If the wrong bitness is found, the script **aborts with a clear message**
   instead of silently building the wrong EXE.

## Recommendation / التوصية

If you only want **one** EXE: build the **32-bit** one
(`build_exe_x86.bat`). It runs on **both** x86 and x64 Windows, and this
app uses only ~21 MB of RAM, so 64-bit's extra memory headroom is never
needed. Build the 64-bit EXE only if you specifically want a native x64
binary.
إذا أردت نسخة واحدة فقط: ابنِ نسخة **32-بت** — تعمل على الاثنين معاً.
