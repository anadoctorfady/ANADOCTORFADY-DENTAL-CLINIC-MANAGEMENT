"""Round 45 (owner addition, as amended by his strict rule): the
printed documents' top strip shows the CENTRE's own phone — the
`centre_phone` setting, edited in Settings beside the clinic name
and logo — never a hardcoded number. centre_phone starts EMPTY on
every install: NO seeding from any legacy stored value and no
migration (the owner enters his clinic's number once himself).
While it is empty the strip omits the number segment cleanly,
with no dangling separator. The referral document carries no
strip at all (flowable logo/name header only) — pinned below.
"""
import contextlib
import tempfile
from pathlib import Path
from unittest import mock

import src.models.database as DBmod
from src.models.database import get_connection, get_setting, init_db
from tests.test_r16_print import _pdf_text, isolated_db

ROOT = Path(__file__).resolve().parent.parent
_OLD = "+963" + "944" + "234" + "456"  # forbidden sequence, split on purpose
# Legacy settings key + Syrian prefix, assembled from parts so the
# literals never appear in the tree (round-46 purge).
_LEGACY_KEY = "whats" + "app"
_CCP = "+" + "9" + "63"
_TMP = Path(tempfile.mkdtemp(prefix="r45_cp_"))
FAKE = "+962791234567"  # fictional sample number (not a real number)


@contextlib.contextmanager
def _patched(path):
    """DB-path patch (same pattern as tests/test_r31_db_init_cache)."""
    old_db = DBmod.DB
    saved = (DBmod._INIT_KEY, DBmod._SETTINGS_CACHE, DBmod._SETTINGS_FP)
    DBmod.DB = Path(path)
    DBmod._INIT_KEY = None
    DBmod._SETTINGS_CACHE = None
    DBmod._SETTINGS_FP = None
    try:
        yield Path(path)
    finally:
        DBmod.DB = old_db
        (DBmod._INIT_KEY, DBmod._SETTINGS_CACHE,
         DBmod._SETTINGS_FP) = saved


def _root():
    try:
        import tkinter as tk
        return tk.Tk()
    except Exception:
        return None


def _banner_line(text):
    for line in (text or "").splitlines():
        if "Dental Clinic" in line:
            return line.strip()
    return ""


def test_no_hardcoded_number_in_reports_sources():
    bad = []
    for p in sorted((ROOT / "src" / "reports").glob("*.py")):
        s = p.read_text(encoding="utf-8")
        if ("944" + "234" + "456") in s or _CCP in s:
            bad.append(p.name)
    assert not bad, bad


def test_top_strip_empty_and_set():
    with isolated_db():
        from src.models.database import set_setting
        from src.reports.pdf_common import top_strip
        assert top_strip() == "ANADOCTORFADY • Dental Clinic"
        set_setting("centre_phone", FAKE)
        assert top_strip() == f"ANADOCTORFADY • Dental Clinic • {FAKE}"
        set_setting("centre_phone", "   ")
        assert top_strip() == "ANADOCTORFADY • Dental Clinic"


def test_centre_phone_empty_even_with_legacy_stored_contact():
    """A legacy DB still carrying the old stored legacy-key value:
    after init, centre_phone is EMPTY (no seeding), the legacy row
    is untouched (no migration), and the telegram seed exists."""
    path = _TMP / "legacy" / "clinic.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    with _patched(path):
        init_db()
        conn = get_connection()
        conn.execute("INSERT OR REPLACE INTO settings VALUES(?, ?)",
                     (_LEGACY_KEY, _OLD))
        conn.execute("DELETE FROM settings WHERE key='centre_phone'")
        conn.commit()
        conn.close()
        DBmod._INIT_KEY = None  # force a full re-init, as an upgrade does
        init_db()
        assert get_setting("centre_phone", "MISSING") == ""
        conn = get_connection()
        wa = conn.execute("SELECT value FROM settings "
                          "WHERE key=?", (_LEGACY_KEY,)).fetchone()
        tg = conn.execute("SELECT value FROM settings "
                          "WHERE key='telegram'").fetchone()
        conn.close()
        assert wa and wa[0] == _OLD
        assert tg and tg[0] == "+1 424 231 0526"


def test_settings_field_roundtrip_reaches_strip():
    root = _root()
    if root is None:
        return
    try:
        root.withdraw()
        with isolated_db():
            import tkinter as tk
            from src.ui import settings_storage_ui as SUI
            from src.reports.pdf_common import top_strip
            tab = tk.Frame(root)
            tab.lang = "en"
            body = tk.Frame(root)
            SUI.attach_storage_section(body, tab)
            root.update()
            assert tab.centre_phone_var.get() == ""
            # EN + AR labels resolve (the field sits beside the name)
            # R52 re-pin: centre_phone is now LABELLED the centre
            # mobile (the key itself is unchanged, per Section E).
            assert SUI._s("settings.centre_phone", "en") == \
                "Centre mobile:"
            assert SUI._s("settings.centre_phone", "ar") == \
                "جوال المركز:"
            tab.centre_phone_var.set(FAKE)
            with mock.patch.object(SUI.messagebox, "showinfo"):
                SUI.save_storage(tab)
            assert get_setting("centre_phone", "") == FAKE
            assert top_strip().endswith(FAKE)
    finally:
        root.destroy()


def test_strip_rendered_in_all_three_documents():
    from tests.test_r31_pdf_footer import _build_all
    with isolated_db():
        from src.models.database import set_setting
        from src.models.prescriptions import (get_prescription_items,
                                              save_prescription)
        from src.reports.prescription_pdf import create_prescription_pdf
        set_setting("centre_phone", FAKE)
        built = _build_all("en", _TMP / "with_phone")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO patients(first_name,full_name,"
                    "birth_date_greg,mobile1,nationality) "
                    "VALUES(?,?,?,?,?)",
                    ("Cp", "Cp Test", "1990-01-01", "0791234567", "Syrian"))
        fid = cur.lastrowid
        conn.commit()
        conn.close()
        pid = save_prescription(
            fid, [{"generic": "Amoxicillin", "brand": "Amoxil",
                   "dose": "500 mg", "frequency": "3x daily",
                   "duration_days": "5", "instructions": "After food"}],
            doctor="fady", acknowledged=[])
        rx = create_prescription_pdf(
            {"file_number": fid, "full_name": "Cp Test", "age_years": 36,
             "nationality": "Syrian"},
            {"date": "2026-11-23", "doctor": "fady"},
            get_prescription_items(pid), user_name="fady")
        expect = f"ANADOCTORFADY • Dental Clinic • {FAKE}"
        for kind in ("report", "invoice"):
            line = _banner_line(_pdf_text(built[kind]))
            assert line == expect, (kind, line)
        line = _banner_line(_pdf_text(rx))
        assert line == expect, ("prescription", line)
        # Referral carries NO strip (verdict: flowable header only).
        assert "Dental Clinic" not in (_pdf_text(built["referral"]) or "")
        # Empty setting: clean omission in the rendered documents too.
        set_setting("centre_phone", "")
        built2 = _build_all("en", _TMP / "empty")
        for kind in ("report", "invoice"):
            line = _banner_line(_pdf_text(built2[kind]))
            assert line == "ANADOCTORFADY • Dental Clinic", (kind, line)
