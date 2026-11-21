# ANADOCTORFADY v2 — Update Guide / دليل التحديثات المستقبلية

> The app is **modular**: every file is <200 lines, every feature lives in
> its own small file, and a test gate runs after every change.
> التطبيق معياري: كل ملف أقل من 200 سطر، وكل ميزة في ملف مستقل،
> وبوابة اختبار بعد كل تعديل.

## Rule 1 — Small, piece-by-piece updates / تحديثات صغيرة قطعة قطعة

- Change **one file at a time**, then run the test gate before the next change:
  ```bat
  python run_tests.py
  ```
  It must print `44/44 test files passed`. If a test fails, fix that file only —
  the fault is isolated to it.
- Never put more than **200 lines** in one `.py` file
  (`python scripts/check_lines.py` enforces this).
- Rebuild the EXE with `installer\build_exe.bat` after the tests pass,
  then rebuild the installer with `installer\build_installer.bat`
  (see `installer\README_BUILD.md` — "Real Windows installer").

## Rule 2 — Data changes need NO code / تغييرات البيانات بدون كود

Most future additions are **JSON edits only** — no Python, no rebuild of
logic. Edit the file, save, run the tests, rebuild the EXE.

| I want to… / أريد أن… | Edit this file |
|---|---|
| Add / change a drug (scientific name + brand) | `src/data/medications.json` |
| Add / change a drug interaction | `src/data/interactions.json` |
| Add a currency or country/nationality | `src/data/currencies.json` / `src/data/countries.json` |
| Add a reusable phrase (complaint, diagnosis…) | `src/data/phrases_seed.json` (or use “＋ حفظ” inside the app — it learns automatically) |
| Change a colour / dark-mode token | `src/config/theme.py` |
| Change the clinic name, WhatsApp, About text | `src/config/settings.py` |

## Rule 3 — Code changes: where to look / تغييرات الكود: أين أجدها

| I want to… / أريد أن… | Edit this file |
|---|---|
| Change the login / password logic | `src/utils/auth.py` |
| Change patient fields / nationality | `src/ui/patient_form.py` |
| Change the dental chart | `src/ui/dental_chart.py` |
| Change complaint / diagnosis / procedures | `src/ui/clinical.py` |
| Change a prescription / interaction alert | `src/ui/prescriptions.py` + `src/models/interactions.py` |
| Change money / exchange rate / finance | `src/models/currency.py` + `src/models/finance.py` |
| Change the patient PDF report | `src/reports/pdf_report.py` |
| Change the prescription PDF | `src/reports/prescription_pdf.py` |
| Add a new table to the database | `src/models/database.py` — add the table in `init_db()` and an `ALTER TABLE` migration for old databases |

## Rule 4 — Never lose patient data / لا تفقد بيانات المرضى

Patient data lives in ONE fixed per-user folder, independent of where
the EXE sits — moving or copying the EXE can no longer lose data:

- Windows: **`%APPDATA%\ANADOCTORFADY`** (`C:\Users\<name>\AppData\Roaming\ANADOCTORFADY`)
  — `clinic.db`, `reports\`, `backups\`, `xrays\`, `scans\`
- Linux: `~/.config/ANADOCTORFADY` — macOS: `~/Library/Application Support/ANADOCTORFADY`

When updating, rebuilding, or reinstalling:
- **Keep** `%APPDATA%\ANADOCTORFADY\clinic.db` and `%APPDATA%\ANADOCTORFADY\reports\`.
- Install the new version with `installer\output\ANADOCTORFADY_Setup.exe` —
  it installs the program to `%LOCALAPPDATA%\ANADOCTORFADY` (a different
  folder) and only replaces the EXE. It never touches the data folder,
  and uninstall never deletes patient data either.
- Copy **only the new `ANADOCTORFADY.exe`** over the old one if you
  install by hand — never copy an old `clinic.db` over the new one.
- Back up first: in the app, Settings → Backup, or copy the whole
  `%APPDATA%\ANADOCTORFADY\` folder somewhere safe.
- Database upgrades are migrations (`ALTER TABLE` in `database.py`), so old
  databases keep working with the new version.
- Coming from a version that stored data next to the EXE: the first run
  of the new version moves the old database automatically (it looks
  next to the EXE, on the Desktop, and in Downloads). The old copy is
  only set aside after the new copy is verified, and kept as
  `clinic.db.migrated-<date>.bak` — never deleted. If the old data was
  somewhere else, copy the old `anadoctorfady\clinic.db` into
  `%APPDATA%\ANADOCTORFADY\` before the first run.

## Lightweight by design / خفيف بالتصميم

- Package **268 KB**, source **2.6 MB**, only **6** external libraries.
- No browser, no server, no background sync — core imports use ~21 MB RAM.
- SQLite (WAL + indexes) handles tens of thousands of patients.
- Keep it that way: do not add heavy frameworks (Electron, web servers,
  cloud SDKs) for a small feature — a JSON file or a <200-line module is
  almost always enough.
