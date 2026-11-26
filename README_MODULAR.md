# ANADOCTORFADY v2 — Modular (each file <200 lines)

Warm Sand Design System v1.0 adopted. Light: bg #F6F1E9, panel #FFFFFF,
card #FAF6F0, text #2C241D, muted #6B5E53, accent #A85F33, border #E3D8CC.
Dark: bg #1A1614, panel #26211E, card #332C28, text #F5F0EB, muted #A3968A,
accent #D97736, border #453D37. Spacing 4px grid, cards radius 12px pad 16px,
buttons 40px radius 8px, inputs 36-40px. Font system-ui / Segoe UI / Tahoma.
Patient Details light brown #E8DCC4, list main theme bg (no pink/violet
wash anywhere since 2026-11-07), names in
iOS27 cycle violet/magenta/orange/teal. Header still iOS27 gradient
#7C3AED → #EC4899 → #F97316. RTL/LTR + bidi isolation for numbers.

## Structure (all <200 lines)
```
main.py (18) - entry only
src/config/theme.py (43) - Warm Sand tokens
src/config/settings.py (25) - clinic, paths, Telegram
src/models/database.py (110) - SQLite core
src/models/finance.py (31) - net income / debts
src/utils/hijri_age.py (57) - Hijri 1990-05-15 = 20 Shawwal 1410
src/utils/arabic.py (27) - reshaper + bidi
src/utils/helpers.py (32) - filenames, nationalities, teeth
src/utils/searchable.py (49) - searchable dropdown (type to filter)
src/utils/nationalities.py (72) - 249 countries, legacy feminine → EN
src/utils/currencies.py (49) - 178 ISO currencies, code ↔ display
src/data/countries.json (249) - country EN/AR + nationality EN/AR
src/data/currencies.json (178) - ISO currency EN/AR + symbol
tests/ + run_tests.py + scripts/check_lines.py + scripts/gate.sh
src/utils/auth.py (25) - fady/1234
src/reports/pdf_styles.py (60) - Noto Arabic fonts
src/reports/pdf_report.py (151) - bilingual PDF
src/ui/login.py (46) / dental_chart.py (64) / patient_form.py (150)
src/ui/clinical.py (138) / appointments.py (53) / finance.py (107)
src/ui/settings_ui.py (54) / shell.py (143)
tests/ + run_tests.py + scripts/check_lines.py + scripts/gate.sh
```

## Test gateway — run after EVERY change
```bash
python3 run_tests.py
bash scripts/gate.sh   # = check_lines + run_tests, fails if any .py >200
```

## Run (Windows 7/8/10/11)
```bat
run.bat
:: or: python -m venv venv & venv\Scripts\activate & pip install -r requirements.txt & python main.py
```
Login: fady / 1234. Reports: anadoctorfady/reports/ as ANADOCTORFADY_<name>.pdf
Build EXE: installer/build_exe.bat (see v1 folder for spec; copy assets/fonts).

## Why small files?
1. Better structure — a bug in one file cannot break the rest; faster to find/fix.
2. Continuous updates — piece-by-piece, small files = fewer tokens per change.

## Dark Mode (added 2026-11-05)
- Toggle in the top bar: **🌙 Dark / ☀️ Light** — switches instantly (rebuilds all
  frames) and persists in setting `theme_mode` (light default).
- Same choice in **Settings > Theme**. Light = Warm Sand above; Dark = Warm
  Charcoal: bg #1A1614, panel #26211E, card #332C28, text #F5F0EB,
  muted #A3968A, accent #D97736, border #453D37.
- Test: `tests/test_theme_mode.py` (tokens differ, mode persists, invalid → light).

## Currency — configurable default (added 2026-11-05)
- Default currency is a **setting** (default SYP), changeable in Settings —
  for a doctor in any country. Supported: **178 ISO currencies** from
  `src/data/currencies.json` (was 11), searchable by code, English or
  Arabic name — type `TRY`, `ليرة تركية` or `Turkish Lira` in Clinical >
  Cost or in Settings > Default currency.
- Rate = units of the **default (base) currency per 1 unit of the payment
  currency**, on the entry date, **entered manually** (offline, no internet).
  If payment currency == base currency, no rate is needed.
- Currency dropdown in Clinical > Cost shows all currencies (default = base).
  The rate label is dynamic, e.g. "USD rate (TRY) on entry date".
  Missing rate for that date → error asking for it; last saved rate is hinted.
- Stored per payment: `currency, exchange_rate, rate_date, total_syp,
  paid_syp, remaining_syp` (the *_syp columns hold base-currency amounts).
  `exchange_rates` is keyed by (date, from_currency, to_currency); old
  date-only rows migrate as USD→SYP.
- Examples: **100 USD × 15000 = 1,500,000 SYP** (base SYP);
  **100 USD × 40 = 4,000 TRY** (base TRY); **50 USD × 0.92 = 46 EUR** (base EUR).
- Net income / debts are summed in the **base currency**; Finance also shows
  the USD equivalent using the latest USD→base rate.
- PDF Cost section shows currency + rate + converted base amount, in both languages.
- Tests: `tests/test_currency.py` (10 checks) + `tests/test_theme_mode.py` (3 checks).
- Test gateway is now **8/8** (was 7/7).

## World data — nationalities & currencies (added 2026-11-05)
- **Nationalities: 249 countries** in `src/data/countries.json` (country +
  nationality in English and Arabic), searchable in the patient form by
  code, country or nationality in either language — type `سوريا`, `Syria`,
  `Turkey` or `تركيا`. Common-name aliases included (Turkey→Türkiye,
  USA→United States, Britain→United Kingdom, Russia, Vietnam, …).
  Default stays **Syrian**; old stored values (Arabic feminine `سورية`,
  English `Syrian`, code `SY`) all open as `Syrian / سوري` and save back
  as English `Syrian`, so existing patients keep working.
- **Currencies: 178 ISO codes** in `src/data/currencies.json`, searchable
  the same way in Clinical > Cost and Settings > Default currency
  (`USD - US Dollar / دولار أمريكي`). The stored value is always the ISO code, so
  rates, conversion and PDFs are unchanged.
- Note: Arabic names for less common currencies fall back to the English
  name in the data file (e.g. `AOA / Kwanza`); search by code or English
  name still works, and the major currencies are fully translated.
- Tests: `tests/test_world.py` (8 checks: counts, search AR/EN incl. `USD`,
  `Egypt`/`مصر`/`مصري`, legacy mapping, currency round-trip, filter).

## Medications, interactions & prescriptions (added 2026-11-05)
- **Medications: 315 drugs** in `src/data/medications.json` — ALL therapeutic classes by scientific (generic) name, not dental-only: antibiotics, analgesics/NSAIDs/opioids, cardiovascular, diabetes, respiratory, GI, CNS, endocrine, immunosuppressants, dermatology, ophthalmology, vitamins. Search by generic scientific name first, then brand, EN+AR; category filter in the prescription tab.
  EN + AR, category, form, strength) — dental antibiotics (Amoxicillin,
  Augmentin, Flagyl, Azithromycin, Clindamycin...), analgesics/NSAIDs,
  corticosteroids, local anaesthetics, antifungals, antivirals, antiseptics,
  plus chronic meds patients take (Warfarin, Aspirin, Clopidogrel, Metformin,
  Insulin, Lisinopril, Atorvastatin, Omeprazole, Levothyroxine, Methotrexate,
  Phenytoin, Carbamazepine...). Searchable in the Prescriptions tab by
  generic or brand, EN or AR — type `Augmentin` or `أموكسيسيلين`.
- **Patient current medications + allergies**: new fields on the patient form
  (comma-separated, stored on the patient record via migration).
- **Drug interactions: 37 pairs** in `src/data/interactions.json`
  (severity severe/moderate/mild, message EN+AR). Class expansion: `NSAID`
  covers Ibuprofen/Diclofenac/Naproxen/..., `Penicillin` covers Amoxicillin/
  Augmentin/Ampicillin/Penicillin V. Examples: Warfarin+Ibuprofen (severe,
  bleeding), Warfarin+Amoxicillin/Metronidazole (severe, INR rise),
  Clopidogrel+Ibuprofen (severe), Methotrexate+NSAIDs (severe),
  Carbamazepine+Erythromycin (severe), Amoxicillin+Allopurinol (moderate).
  Allergy check: penicillin allergy + any penicillin = severe red alert;
  sulfa allergy + sulfamethoxazole = severe.
- **Colored live alerts**: selecting a drug runs the check against the
  patient's current meds, allergies and drugs already on this prescription.
  Severe = red (#DC2626 on #FEE2E2), moderate = amber (#D97706 on #FEF3C7),
  mild = yellow. A severe alert requires ticking "I understand the risk and
  want to continue" before the prescription can be saved.
- **Prescriptions are ALWAYS saved in the patient file** (`prescriptions` +
  `prescription_items` tables, with date, doctor, notes and any acknowledged
  warnings) — whether printed or not. History list per patient with a
  Print button. Print generates a bilingual PDF
  `ANADOCTORFADY_RX_<patient>_<date>.pdf` in `reports/` (clinic header,
  patient info, drug/dose/frequency/duration, acknowledged warnings,
  doctor signature space, date + entering username).
- **Safety disclaimer** (shown in the UI and on the Rx PDF): interaction data
  is a curated aid only and does NOT replace clinical judgment — always
  verify before prescribing.
- Tests: `tests/test_prescriptions.py` (5 checks: Augmentin search,
  Warfarin+Ibuprofen severe, penicillin allergy severe, safe combo
  Paracetamol+Amlodipine, save round-trip + Rx PDF).
- Test gateway is now **9/9** (was 8/8).

## Reusable phrases memory + clipboard history (added 2026-11-05)
- **Reusable phrases (ذاكرة العبارات الجاهزة)**: table `reusable_phrases`
  (category, text UNIQUE, usage_count, last_used, is_favorite). Categories:
  complaint, symptom, diagnosis, procedure, service, note.
- **Auto-learning**: every complaint / symptom / diagnosis / procedure the
  doctor saves is stored as a reusable phrase (deduplicated — the second
  time it only bumps `usage_count`). The doctor never retypes the same
  complaint from scratch for the next patient.
- **Seeded with 105 ready phrases** in `src/data/phrases_seed.json`
  (complaint 21, symptom 18, diagnosis 20, procedure 19, service 17,
  note 10), loaded only on first use if the table is empty. Examples:
  complaint "ألم حاد في السن عند المضغ", "تورم في اللثة", "نزيف اللثة عند
  التفريش"; symptom "ألم نابض", "حساسية للبارد"; diagnosis "تسوس عميق",
  "التهاب لب السن", "خراج سني"; procedure "حشوة تجميلية", "علاج عصب (جذر)",
  "تنظيف وتلميع", "خلع سن".
- **UI (Clinical tab, under every field)**: a "📋 جاهز:" row per field —
  type to filter live, click to insert (Append = default, or Replace),
  "＋ حفظ" saves the current text as a template, "⭐" toggles favourite.
  Top phrases are ordered favourites first, then most-used, then most recent.
- **Clipboard history (Clipdiary-like)**: table `clipboard_history`
  (max 30 items, consecutive duplicates ignored). Button
  "📋 Clipboard / الحافظة (Ctrl+Shift+V)" in the Clinical tab opens a panel
  with the last 20 copied texts — click to paste into the focused field.
  While open it polls the system clipboard every 2s, so text copied in
  **Clipdiary or any other program** appears here automatically and can be
  reused repeatedly. Normal Ctrl+V paste from Clipdiary also works as usual.
- Tests: `tests/test_phrases.py` (4 checks: seed >=20, save dedupes and
  counts, top ordered by usage, clipboard add/list/dedupe/clear).
- Test gateway was **11/11** at that point (now 12/12 with test_arch).

## Installer package (v2-final) / حزمة التثبيت

- **No EXE is built in this Linux environment.** The zip is a Windows-ready
  installer package: run `installer/build_exe.bat` on Windows to build
  `dist/ANADOCTORFADY.exe` (see `installer/README_BUILD.md`).
- `installer/ANADOCTORFADY.spec` — PyInstaller onefile/windowed spec, entry
  `main.py`, datas `assets/` + `src/` (fonts + 5 JSON data files), hiddenimports
  for reportlab/openpyxl/hijri/arabic-reshaper/bidi/PIL/sqlite3/tkinter.
- `installer/build_exe.bat` — venv + `pip install -r requirements.txt` +
  PyInstaller (5.13 on Windows 7, latest on Win10/11) + build.
- **Frozen-path fix (v2-final):** `src/config/settings.py` is frozen-aware —
  in the EXE, `clinic.db` / `reports/` / `backups/` / `xrays/` are created
  **next to the EXE**, not in the PyInstaller temp folder (verified with a
  simulated `sys.frozen` run). Fonts resolve via `sys._MEIPASS` when frozen.
- `UPDATE_GUIDE.md` — how to update in future (JSON edits need no code,
  one small <200-line file at a time, test gate, keep clinic.db + reports).

## Anonymous usage statistics (silent automatic, count + countries only)

- **Always ON (silent, owner's decision, NO off switch).** No consent dialog, no
  ask-once flow. Settings holds only the server URL field.
- **Sent (max once every 4 hours, 3s timeout, background thread, silent offline):**
  exactly `{install_id, app_version, platform}` — a random UUID, the app
  version, `windows`. Nothing else.
- **Never sent:** patient data, names, emails, phones, country (derived
  server-side from IP, then IP discarded), location/GPS, usage details, IP.
- **No server URL configured (default empty) = nothing is ever sent.**
  Fady must host `server/telemetry_server.py` (stdlib only, port 8000)
  and paste its URL in Settings first — see
  `server/README.md`. Server stores only `(date, country_code,
  sha256(install_id))`; `POST /ping` rejects extra fields;
  `GET /stats?token=...` returns `{total_users, users_by_country,
  last_30_days}`; `GET /` shows a small HTML table.
- Tests: `tests/test_telemetry.py`. Test gateway is now **14/14**.

## x86 (32-bit) vs x64 (64-bit) / هل يعمل على x86 و x64؟

- **Yes — with a 32-bit Python build.** The source code and SQLite work on
  both; a PyInstaller EXE is architecture-specific, so the Python used to
  build decides: **32-bit Python → EXE runs on x86 AND x64** (recommended,
  one EXE for every PC); 64-bit Python → EXE runs on x64 only.
- `installer/build_exe.bat` detects the Python architecture at the start
  (`struct.calcsize("P")*8`), prints it, warns and asks before continuing
  with a 64-bit-only build, and saves the result also as
  `ANADOCTORFADY_x86.exe` (32-bit) or `ANADOCTORFADY_x64.exe` (64-bit).
- The app has **no architecture-specific code** (no hardcoded Program Files /
  System32 paths, no 64-bit-only dependency) — enforced by
  `tests/test_arch.py`. Test gateway is now **14/14**.
- Full explanation + how to download 32-bit Python: `installer/README_BUILD.md`
  ("x86 vs x64" section). The 64-bit build's extra RAM headroom is irrelevant
  here — the app uses ~21 MB.

## Activation — REMOVED (owner decision, 2026-11-05)

- Activation was **removed entirely**: no activation window, no Machine ID,
  no code, no secret. The app is auto-activated and opens straight to login
  (`fady / 1234`). See `ACTIVATION_REMOVED.md`. Guard: `tests/test_no_activation.py`.

## Logo (ANADOCTORFADY)

- Gold tooth + crown logo, transparent background, with the name
  `ANADOCTORFADY` baked in: `assets/logo_anadoctorfady.png` (also
  `assets/logo_transparent.png`, `assets/logo_corner.png` for the top bar).
  Windows icon `assets/app.ico` (16/32/48/256). Login screen: logo on top
  (~140 px), fields BELOW it (layout B, chosen by the owner); top-bar corner
  (~40 px) sits directly on the header background — no black square.
  Warm Sand / Warm Charcoal colors are unchanged.
- The built EXE embeds the icon (`installer/ANADOCTORFADY.spec`
  `icon='../assets/app.ico'`); the Desktop shortcut created by
  `installer/create_shortcut.vbs` (or right-click → Send to Desktop) uses
  the same icon. Helper: `src/utils/logo.py` (39 lines, frozen-aware,
  never crashes if the logo is missing).

## Security: reverse engineering + code signing (honest)

- No method makes reverse engineering impossible: a PyInstaller one-file
  EXE can be unpacked and decompiled. PyArmor obfuscation (optional
  `installer/build_obfuscated.bat`) only raises the bar; `--key` is
  deprecated and not used; never put secrets in the code. Full details:
  `SECURITY.md`.
- Without a paid code-signing certificate, Windows SmartScreen **will**
  show "Windows protected your PC / Unknown publisher" on first run — not
  an error; click "More info → Run anyway". Removing it needs an OV
  certificate (~$200–400/year) or EV (more, immediate reputation) from a
  public CA; self-signed does not help. Build scripts sign optionally when
  `CERT_PFX` + `CERT_PASS` are set (signtool); otherwise they skip signing
  with a note and the build still succeeds.
