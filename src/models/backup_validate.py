"""Restore validation for .bak / .db / .sql backups (Item 9).

A .bak file from another program is just a SQLite database with a
different extension, so restore_db() in database.py (which only knows
.db/.sql) cannot take it. This module validates FIRST and only then
touches the live clinic.db:

1. validate: the file must be a real SQLite database containing the
   clinic schema (patients table at minimum); a text file, a random
   binary, or a SQLite DB from another app is refused and NOTHING
   changes.
2. auto-backup: the current clinic.db is backed up (backup_db) before
   any restore, so a bad restore can always be undone.
3. restore: .bak/.db are copied over clinic.db (stale -wal/-shm
   removed first so they cannot shadow the restored file); .sql goes
   through restore_db(); then init_db() re-creates any missing tables
   and the caller reloads the app (App._rebuild) so restored data shows.
"""
import shutil
import sqlite3
from pathlib import Path

from src.models.database import DB, backup_db, init_db, restore_db

# Round 17 (language purity): user-visible messages are SINGLE-language.
# BAD_MSG / OK_MSG keep the legacy bilingual text for import compat only;
# validate/restore return bad_msg(lang) / ok_msg(lang) (lang=None ->
# the app language from the 'language' setting).
BAD_MSG = ("Invalid backup file / ملف النسخة الاحتياطية غير صالح:\n"
           "not a clinic database (patients table missing) — nothing was changed.\n"
           "ليس قاعدة بيانات عيادة (جدول المرضى غير موجود) — لم يتغير أي شيء.")
_BAD = {"en": "Invalid backup file:\nnot a clinic database (patients table missing) — nothing was changed.",
        "ar": "ملف النسخة الاحتياطية غير صالح:\nليس قاعدة بيانات عيادة (جدول المرضى غير موجود) — لم يتغير أي شيء."}
_OK = {"en": "Restored successfully.\nA backup of the previous database was saved first.",
       "ar": "تمت الاستعادة بنجاح.\nتم حفظ نسخة احتياطية من قاعدة البيانات السابقة أولاً."}
def _lang(lang):
    if lang in ("en", "ar"):
        return lang
    try:
        from src.models.database import get_setting
        return "ar" if (get_setting("language", "en") or "en") == "ar" else "en"
    except Exception:
        return "en"
def bad_msg(lang=None):
    return _BAD[_lang(lang)]
def ok_msg(lang=None):
    return _OK[_lang(lang)]
# Columns the clinic schema needs: init_db() creates indexes on
# full_name/mobile1/mobile2/emergency_phone, so a "patients" table
# without them (e.g. a minimal table from another program) would
# break the app mid-restore. Such files are refused up front.
REQUIRED_PATIENT_COLUMNS = {"file_number", "first_name", "full_name",
                            "mobile1", "mobile2", "emergency_phone",
                            "birth_date_greg"}
OK_MSG = _OK["en"] + " / " + _OK["ar"]  # legacy bilingual, compat only


def validate_backup_file(path, lang=None):
    """(ok, message): True only for a SQLite DB holding the clinic schema.

    .sql dumps are checked by text: they must mention the patients table.
    Never raises for a bad file — returns (False, bad_msg(lang)).
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False, (("الملف غير موجود: " if _lang(lang) == "ar" else "File not found: ") + str(p))
    if p.suffix.lower() == ".sql":
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return False, bad_msg(lang)
        if "patients" in text and "CREATE TABLE" in text:
            return True, ""
        return False, bad_msg(lang)
    if p.suffix.lower() not in (".db", ".bak"):
        return False, bad_msg(lang)
    try:
        conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        try:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(patients)")}
            if not REQUIRED_PATIENT_COLUMNS <= cols:
                return False, bad_msg(lang)
            if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                return False, bad_msg(lang)
        finally:
            conn.close()
    except Exception:
        return False, bad_msg(lang)
    return True, ""


def restore_backup_safe(path, lang=None):
    """Validate -> auto-backup current DB -> restore. (ok, msg, auto_backup).

    On failure (invalid file) returns (False, bad_msg(lang), None) and the
    live database is untouched — no backup is even taken.
    """
    ok, msg = validate_backup_file(path, lang)
    if not ok:
        return False, msg, None
    try:
        auto = backup_db()
    except Exception as e:
        # Current DB cannot be backed up (locked/corrupt): refuse the
        # restore rather than risk losing it. Nothing is changed.
        _m = ("تعذر نسخ قاعدة البيانات الحالية احتياطياً، تم رفض الاستعادة: " if _lang(lang) == "ar"
              else "Cannot back up the current database, restore refused: ")
        return False, (_m + str(e)), None
    p = Path(path)
    try:
        if p.suffix.lower() == ".sql":
            restore_db(p)
        else:
            for suf in ("-wal", "-shm"):
                side = Path(str(DB) + suf)
                if side.exists():
                    side.unlink()
            shutil.copy2(p, DB)
            init_db()
        # Safety net: a .bak copied while its source had uncheckpointed
        # WAL frames can be corrupt — verify, and roll back to the
        # auto-backup instead of leaving a broken live database.
        chk = sqlite3.connect(str(DB))
        try:
            good = chk.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        finally:
            chk.close()
        if not good:
            raise ValueError("restored database failed integrity_check")
    except Exception as e:
        try:
            for suf in ("-wal", "-shm"):
                side = Path(str(DB) + suf)
                if side.exists():
                    side.unlink()
            shutil.copy2(auto, DB)
            init_db()
        except Exception:
            pass
        _m = ("فشلت الاستعادة: " if _lang(lang) == "ar" else "Restore failed: ") + str(e)
        _m += ("\nتم نسخ قاعدة البيانات السابقة احتياطياً إلى:\n" if _lang(lang) == "ar"
               else "\nYour previous database was backed up to:\n") + auto
        return False, _m, auto
    return True, ok_msg(lang), auto


def export_backup(dest_path):
    """Export the current DB to dest (.bak or .db). Returns the path str.

    backup_db(custom=...) copies clinic.db and also writes a .sql dump
    next to it; the .bak itself is a byte-identical SQLite database,
    so it restores anywhere via restore_backup_safe().
    """
    dest = Path(dest_path)
    if dest.suffix.lower() not in (".bak", ".db"):
        dest = dest.with_suffix(".bak")
    return backup_db(custom=dest)
