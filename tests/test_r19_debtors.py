"""Round 19 (R19-E): Debtors-only toggle in the patient list.

Seeds a debtor (remaining > 0), a fully-paid patient and a
soft-deleted debtor (must stay hidden). Toggle ON -> the list
shows ONLY the debtor; toggle OFF -> the previous search-only
list behaviour is restored exactly (round-16 semantics: no
criteria + no open patient = empty list; open patient = just
them). The balance comes from patient_totals() -- GUI test with
a stub holding the real tree/panel, like test_r16_patients_search.
"""
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

from src.models.database import get_connection, init_db, save_financial
from src.models.finance import patient_totals
from src.models.patients import save_patient_record, soft_delete_patient
from src.ui.patient_search import AdvancedSearchPanel
from src.ui.shell import App

TODAY = "2026-11-14"


def _seed(first, father, last):
    return save_patient_record({
        "first_name": first, "father_name": father, "grand_name": "",
        "last_name": last,
        "full_name": " ".join(p for p in (first, father, last) if p),
        "birth_date_greg": "1990-05-15", "birth_date_hijri": "",
        "age_years": 0, "age_months": 0, "age_days": 0, "age_total_days": 0,
        "age_hijri_years": 0, "age_hijri_months": 0, "age_hijri_days": 0,
        "mobile1": "0911000000", "mobile2": "", "emergency_phone": "",
        "address": "", "nationality": "Syrian", "current_medications": "",
        "allergies": "", "diseases": ""})


def _cleanup(*fids):
    conn = get_connection(); cur = conn.cursor()
    for fid in fids:
        cur.execute("DELETE FROM financials WHERE patient_file=?", (fid,))
        cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    conn.commit(); conn.close()


def _rows(stub):
    return [stub.tree.item(i, "values") for i in stub.tree.get_children()]


def test_debtors_toggle_filters_list():
    init_db()
    # The isolated gate DB is a copy of the LIVE database, which
    # already holds real debtors -- expectations are set-based:
    # (pre-existing live debtors) + the seeded debtor, nothing else.
    conn = get_connection()
    live_ids = [r[0] for r in conn.execute(
        "SELECT file_number FROM patients WHERE COALESCE(deleted,0)=0")]
    conn.close()
    before = {fid for fid in live_ids
              if patient_totals(fid)["remaining"] > 0}
    debtor = _seed("R19Debtor", "R19Dad", "R19Fam")
    paid = _seed("R19Paid", "R19Dad", "R19Fam")
    gone = _seed("R19Gone", "R19Dad", "R19Fam")
    save_financial(debtor, "11", 100000, 40000, TODAY,
                   doctor="fady", entered_by="fady")   # remaining 60000
    save_financial(paid, "11", 50000, 50000, TODAY,
                   doctor="fady", entered_by="fady")    # remaining 0
    save_financial(gone, "11", 90000, 0, TODAY,
                   doctor="fady", entered_by="fady")    # remaining 90000
    assert soft_delete_patient(gone) is True
    assert patient_totals(debtor)["remaining"] == 60000.0
    assert patient_totals(paid)["remaining"] == 0.0
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        _cleanup(debtor, paid, gone)
        print("SKIP test_debtors_toggle_filters_list (no display)")
        return
    try:
        tree = ttk.Treeview(root, columns=("file", "name", "mobile"),
                            show="headings")
        tree.pack()
        stub = SimpleNamespace(tree=tree, search_var=tk.StringVar(),
                               adv_search=None, current_patient=None,
                               lang="en")
        stub.load_patients = lambda: App.load_patients(stub)
        panel = AdvancedSearchPanel(root, stub,
                                    on_search=lambda: App.load_patients(stub))
        panel.pack(); stub.adv_search = panel; root.update_idletasks()
        # Model helper: pre-existing debtors + the seeded debtor;
        # the fully-paid and the soft-deleted debtor never qualify.
        want = before | {debtor}
        got = {r["file_number"] for r in panel.debtor_rows()}
        assert got == want, (got, want)
        assert paid not in got and gone not in got
        # Normal behaviour first: no criteria, no open patient -> empty.
        App.load_patients(stub)
        assert _rows(stub) == []
        # ON: exactly the debtor set (paid + soft-deleted hidden).
        panel.toggle_debtors(); root.update_idletasks()
        assert panel.debtors_only is True
        rows = _rows(stub)
        assert {str(r[0]) for r in rows} == {str(x) for x in want}, rows
        assert "✓" in panel.btn_debtors.cget("text")
        # A shell refresh while ON (quick-search path) keeps the filter.
        stub.load_patients(); root.update_idletasks()
        rows = _rows(stub)
        assert {str(r[0]) for r in rows} == {str(x) for x in want}, rows
        # OFF: previous behaviour restored exactly.
        panel.toggle_debtors(); root.update_idletasks()
        assert panel.debtors_only is False
        assert _rows(stub) == []
        stub.current_patient = {"file_number": paid}
        stub.load_patients(); root.update_idletasks()
        rows = _rows(stub)
        assert len(rows) == 1 and str(rows[0][0]) == str(paid), rows
    finally:
        root.destroy(); _cleanup(debtor, paid, gone)


def test_debtors_strings_bilingual():
    from src.config.strings import t
    assert t("patients.debtors_only", "en") == "Debtors only"
    assert t("patients.debtors_only", "ar") == "المديونون فقط"
    assert t("patients.debtors_only_on", "en") == "✓ Debtors only"
    assert t("patients.debtors_only_on", "ar") == "✓ المديونون فقط"
