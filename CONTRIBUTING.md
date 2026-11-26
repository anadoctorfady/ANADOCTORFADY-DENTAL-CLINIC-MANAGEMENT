# Contributing to ANADOCTORFADY

Thank you for helping make this free dental clinic system better!
شكراً لمساعدتك في تحسين نظام عيادة الأسنان المجاني هذا!

## How to contribute / كيف تساهم

1. **Fork** the repository and create a branch for your change
   (`feature/...` or `fix/...`).
2. Make your change, then run the test gate before opening a pull request:
   ```bat
   python run_tests.py
   ```
   Expected: **44/44 test files passed**.
3. Open a pull request describing what changed and why, in English or Arabic.

## Rules / القواعد

- **No Python file over 200 lines** — the app is modular on purpose, so a
  fault in one file cannot break the rest. Split a file instead of growing it
  (`scripts/check_lines.py` enforces this).
- **Data lists are JSON, not code** — medications, interactions, currencies,
  countries and seed phrases live in `src/data/*.json` and are editable
  without touching Python.
- **Bilingual** — user-visible text should exist in English and Arabic.
- **No patient data, no secrets, no credentials** in any commit, ever.
  The `.gitignore` blocks databases, runtime output and secret files —
  do not work around it.
- **Privacy** — telemetry (if you touch it) stays count + countries only:
  never add names, patient data, GPS, or stored IPs.

## Where to start / من أين تبدأ

Good first issues: a translation fix, a new reusable phrase, a missing drug
or interaction (with a source), a UI polish, or a new test. Ask on Telegram
+1 424 231 0526 if you are unsure.
