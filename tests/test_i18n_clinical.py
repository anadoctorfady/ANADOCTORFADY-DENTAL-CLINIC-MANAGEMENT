"""i18n for Patients + Clinical (Job A2).

(1) GUI test under xvfb: toggle to Arabic, build the App, assert the
Patients + Clinical tabs show Arabic labels (form labels, table
headings, Templates buttons, Cost + prescription sections, chart
headings, notes); toggle back and assert English returns. Skips
gracefully with no display. (2) Static test: every t("...") key used
in the 9 owned source files must exist in both EN and AR in the
MERGED strings (strings.py) plus the round-16 modules.
"""
import importlib
import re
from pathlib import Path

from src.config.strings import AR as _AR, EN as _EN
ROOT = Path(__file__).resolve().parent.parent
EN, AR = dict(_EN), dict(_AR)
for _name in ("strings_r16_clinical", "strings_r16_patients",
              "strings_r16_print", "strings_r16_rx",
              "strings_r16_settings"):
    _mod = importlib.import_module(f"src.config.{_name}")
    EN.update(_mod.EN); AR.update(_mod.AR)
OWN_FILES = ["patient_form.py", "clinical.py", "clinical_money_strip.py",
             "clinical_tables.py", "clinical_lists.py", "prescriptions.py",
             "dental_chart.py", "scans_tab.py"]  # R21 item 5: notes_tab.py deleted with the (Optional) notes section; R40: clinical_finance.py -> clinical_money_strip.py
KEY_RE = re.compile(r'"((?:patient|clinical|rx|notes|chart|scans)\.[a-z_]+)"')

def _used_keys():
    """Every clinical-area key literal in the 9 owned files: t("...")
    call args AND the key-mapping dicts (TITLES / ADD_BTNS /
    FIELD_LABELS / COL_KEYS / XRAY_COL_KEYS / FILETYPES)."""
    keys = set()
    for name in OWN_FILES:
        keys |= set(KEY_RE.findall((ROOT / "src" / "ui" / name).read_text(encoding="utf-8")))
    return keys

def test_i18n_clinical_keys_exist_in_both_languages():
    keys = _used_keys()
    assert keys, "no i18n keys found in owned files"
    assert set(EN) == set(AR), "EN/AR key sets differ in merged strings + r16 modules"
    missing_en = sorted(k for k in keys if k not in EN)
    missing_ar = sorted(k for k in keys if k not in AR)
    assert not missing_en, f"keys missing from EN: {missing_en}"
    assert not missing_ar, f"keys missing from AR: {missing_ar}"
    for k in keys:
        assert EN[k], f"empty EN value: {k}"
        assert AR[k], f"empty AR value: {k}"

def test_i18n_clinical_dicts_only_en_ar():
    import src.config.strings_clinical as mod
    public = {n for n in dir(mod) if not n.startswith("_")}
    assert public == {"EN", "AR"}, public

def _texts(widget, out=None):
    """All user-visible texts under a widget: Label/Button/
    Radiobutton/Checkbutton/Labelframe text + Treeview headings."""
    if out is None:
        out = []
    try:
        if widget.winfo_class() in ("Label", "Button", "Radiobutton",
                                    "Checkbutton", "Labelframe"):
            out.append(widget.cget("text") or "")
    except Exception:
        pass
    try:
        if widget.winfo_class() == "Treeview":
            for c in widget["columns"]:
                out.append(widget.heading(c, "text") or "")
    except Exception:
        pass
    for ch in widget.winfo_children():
        _texts(ch, out)
    return out

def _tab_texts(notebook):
    try:
        return [notebook.tab(i, "text") for i in range(notebook.index("end"))]
    except Exception:
        return []

def _stub_app(lang):
    """Minimal app stand-in (same shape as test_clinical_redesign's):
    builds the two tab widgets without the full shell.

    NOTE: the full App() cannot be constructed right now -- the
    Finance tab (another worker's area) raises NameError in
    finance_views.recolour_tab_frame (its `t` parameter was renamed
    to `th` in the body but not in the signature), so the shell's
    _main() fails before the Patients/Clinical tabs exist. This test
    therefore builds PatientForm + ClinicalTab directly, which is
    exactly the area under test here."""
    class FakeApp:
        current_patient = None
        current_user = "fady"
        current_role = "admin"

        def chart_teeth(self):
            return []

        def refresh_clinical(self):
            pass

        def on_teeth_select(self, teeth, typ):
            pass

        def load_patients(self):
            pass

        def select_patient(self, fid):
            pass

        def print_pdf(self):
            pass

    app = FakeApp()
    app.lang = lang
    return app

def _build_tabs(lang):
    """(root, form, clinical) for `lang`, or (None, None, None) with
    no display."""
    import tkinter as tk
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None, None
    root.withdraw()
    try:
        from src.ui.patient_form import PatientForm
        from src.ui.clinical import ClinicalTab
        app = _stub_app(lang)
        form = PatientForm(root, app)
        form.pack()
        clinical = ClinicalTab(root, app)
        clinical.pack()
        app.current_patient = {"full_name": "Ahmed Mohammed Ali Hassan",
                               "file_number": 1, "mobile1": "0944000111",
                               "birth_date_greg": "1990-05-15"}
        clinical._refresh_patient_panel()
        root.update_idletasks()
        return root, form, clinical
    except Exception:
        root.destroy()
        raise

def test_clinical_arabic_labels_in_app():
    """GUI test under xvfb; returns (skips) with no display. Builds
    the Patients + Clinical tabs in Arabic, asserts the key labels
    are Arabic, then rebuilds in English and asserts they return."""
    root, form, clinical = _build_tabs("ar")
    if root is None:
        print("SKIP test_clinical_arabic_labels_in_app (no display)")
        return
    try:
        texts = _texts(form) + _texts(clinical)
        # R24: the top notebook (history_top_nb) is REMOVED with
        # the unified table; only the bottom notebook remains.
        tabs = _tab_texts(clinical.history_nb)
        blob = "\n".join(texts + tabs)
        # Patients tab: form labels + chart headings. (Round 20: the
        # "رقم الملف: 1" needle went with the removed clinical header.)
        for needle in ("الاسم الأول", "اسم الأب", "تاريخ الميلاد",
                       "التاريخ الهجري", "العمر (ميلادي)", "الجنسية",
                       "حفظ", "لوحة الأسنان", "الفك العلوي",
                       "الفك السفلي", "دائم"):
            assert needle in blob, f"missing AR in Patients: {needle}"
        # Clinical tab: sections, cost, prescriptions, notes.
        # R40: "إضافة دفعة" (Add Payment) is GONE with its zone —
        # one payment place; the money labels below remain.
        for needle in ("الشكوى", "الأعراض", "التشخيص", "الإجراء",
                       "المجموع", "المدفوع", "المتبقي",
                       "العملة", "الطبيب المعالج", "الوصفة الطبية",
                       "إضافة دواء", "إضافة دواء جديد", "حفظ الوصفة",
                       "سجل الوصفات", "ملاحظات", "المريض",
                       "التاريخ", "السن", "قوالب"):
            assert needle in blob, f"missing AR in Clinical: {needle}"
        # R24: the Diagnosis/Procedures notebook tabs are REMOVED
        # (unified table); the remaining notebook tabs are asserted.
        for needle in ("استعراض المدفوعات", "الأشعة", "المسح"):  # R38: المالية -> استعراض المدفوعات
            assert any(needle in t for t in tabs), f"missing AR history tab: {needle}"
    finally:
        root.destroy()
    root, form, clinical = _build_tabs("en")
    assert root is not None, "display vanished between builds"
    try:
        blob = "\n".join(_texts(form) + _texts(clinical))
        # Round 20: "File #: 1" went with the removed header (above).
        for needle in ("First Name", "Birth (DD/MM/YYYY)", "Save",
                       "Dental Chart", "Complaint", "Diagnosis",
                       "Total", "Paid", "Remaining",  # R40: "Add Payment" gone with its zone
                       "Prescription", "Add Drug", "Save Prescription",
                       "Notes"):
            assert needle in blob, f"missing EN after toggle back: {needle}"
    finally:
        root.destroy()
