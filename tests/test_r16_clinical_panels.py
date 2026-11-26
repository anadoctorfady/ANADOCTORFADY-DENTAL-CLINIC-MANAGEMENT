"""Round 16 items 1 + 14: Health-panel diseases line, the
refresh_right_panels contract, and the interactive panels (header
click collapses, row click opens the detail). The compact patient
header that item 14 originally built was REMOVED in round 20.
Round 22 supersedes that again: the tab opens with a PINNED
HEADER (tab.header_panel), build_panels builds only payments +
procedures (main scroll flow), and the "rx" summary panel is
superseded by tab.rx_section.tree_hist. Round 23 supersedes the
payments parts (panel REMOVED): collapse uses "procedures", the
refresh contract's payment leg is asserted on the History /
Financial trees after load(), and the row-click payment detail
via its migrated home on History rows (clinical_history).
GUI tests skip with no display. (_health / _rx_hist helpers live
in test_clinical_panels.)"""
import tkinter as tk
from unittest import mock
from src.models.database import get_connection
from src.models.prescriptions import save_prescription
from src.ui import clinical_history as _hist_r23
from src.ui import clinical_panel_interact as _interact
from src.ui.clinical import ClinicalTab
from src.ui.clinical_panels import (diseases_list, format_meds, refresh_right_panels)
from tests.test_clinical_panels import (_cleanup, _health, _rx_hist, _seed_payment, _seed_rx, _seed_patient)

class _FakeApp:
    lang = "en"; current_user = "fady"; current_role = "admin"
    def __init__(self, lang="en", patient=None):
        self.lang = lang; self.current_patient = patient
    def chart_teeth(self): return []
    def refresh_clinical(self): pass

def _build(lang="en", patient=None):
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.geometry("1380x900")
    root.deiconify()
    tab = ClinicalTab(root, _FakeApp(lang, patient))
    tab.pack(fill="both", expand=True)
    root.update()
    return root, tab

def _panel_text(tab, key):
    return tab.panel_texts[key].get("1.0", tk.END)

def test_r16_health_panel_diseases_line():
    assert diseases_list({"diseases": "Diabetes, Hypertension"}) == \
        ["Diabetes", "Hypertension"]
    assert diseases_list({"diseases": ""}) == []
    assert diseases_list({}) == []  # column missing -> "None", no crash
    assert diseases_list(None) == []
    lines = format_meds({"medicines": ["Aspirin"], "allergies": []}, "en", diseases=["Diabetes"])
    assert lines[0] == "Diseases: Diabetes", lines
    assert lines[1] == "Medicines: Aspirin" and lines[2] == "Allergies: None"
    lines = format_meds({"medicines": [], "allergies": []}, "en", diseases=[])
    assert lines[0] == "Diseases: None", lines
    lines = format_meds({"medicines": [], "allergies": []}, "ar", diseases=["السكري"])
    assert lines[0].startswith("الأمراض:") and "السكري" in lines[0]
    # diseases=None keeps the old two-line output (round-15 compat).
    assert format_meds({"medicines": [], "allergies": []}, "en") == ["Medicines: None", "Allergies: None"]

def test_r16_refresh_right_panels_contract():
    assert callable(refresh_right_panels)
    fid = _seed_patient("Amoxicillin 500 mg", "Penicillin")
    try:
        _seed_rx(fid, "fady", ["Amoxicillin"])
        patient = {"file_number": fid, "full_name": "R16 Panel Test", "mobile1": "", "birth_date_greg": "1990-01-01", "diseases": "Diabetes", "current_medications": "Amoxicillin 500 mg", "allergies": "Penicillin"}
        root, tab = _build("en", patient)
        if tab is None:
            print("SKIP test_r16_refresh_right_panels_contract (no display)")
            return
        try:
            tab.load(fid)
            root.update()
            # Round 22: Diseases lives in the pinned header (was the
            # "meds" panel); the seeded Rx is in tree_hist.
            assert "Diseases: Diabetes" in _health(tab, "diseases")
            assert "Amoxicillin" in _rx_hist(tab)
            # Round 22 Rx contract: refresh_right_panels no longer
            # drives an Rx panel (superseded by the full Rx section),
            # so a model-saved Rx appears in tree_hist only after
            # tab.rx_section.load(fid) reloads the history.
            save_prescription(fid, [{"generic": "Ibuprofen", "brand": "", "dose": "400 mg", "frequency": "x3", "duration_days": "3", "instructions": ""}], doctor="fady")
            assert "Ibuprofen" not in _rx_hist(tab)
            refresh_right_panels(tab)
            root.update()
            assert "Ibuprofen" not in _rx_hist(tab)
            tab.rx_section.load(fid)
            root.update()
            assert "Ibuprofen" in _rx_hist(tab)
            # R23 supersedes the PAYMENTS refresh leg: panel gone,
            # so a payment seeded after load is absent from the
            # Financial tree until tab.load picks it up.
            _seed_payment(fid, "2026-11-02", "21", 77777, 77777)
            fin = lambda: " ".join(str(v) for i in tab.tree_fin.get_children() for v in tab.tree_fin.item(i, "values"))
            assert "77777" not in fin()
            tab.load(fid)
            root.update()
            assert "77777" in fin()
        finally:
            root.destroy()
    finally:
        _cleanup(fid)

def test_r22_header_and_main_flow_panels():
    """Round 22 supersedes the round-20 spec pinned by the old
    test_r20_no_info_block_panels_top_column: the tab now OPENS
    with a pinned header -- the old header / info / alert widget
    names live on tab.header_panel (PatientInfoPanel), NOT on the
    tab -- and the payments / procedures panels sit in the main
    scroll flow AFTER the history section (tab.panels_section
    comes after tab.history_section in right_inner pack order)."""
    fid = _seed_patient("", "")
    try:
        patient = {"file_number": fid, "full_name": "Ahmed Mohammed Ali Hassan", "age_years": 36, "birth_date_greg": "1990-05-15", "mobile1": "0794000111", "current_medications": "", "allergies": "Penicillin"}
        root, tab = _build("en", patient)
        if tab is None:
            print("SKIP test_r22_header_and_main_flow (no display)")
            return
        try:
            tab.load(fid)
            root.update()
            # No trace of the old block ON THE TAB (round-22 spec).
            for attr in ("lbl_pat_name", "lbl_pat_meta", "patient_header_frame", "clin_info_panel", "alert_strip", "left_info_frame"):
                assert not hasattr(tab, attr), attr
            # The pinned header shows the patient (name + allergy).
            assert "Ahmed Mohammed Ali Hassan" in tab.header_panel._name_lbl.cget("text")
            assert "Penicillin" in _health(tab, "allergies")
            # ROUND-24 SUPERSESSION: the panels section is REMOVED;
            # the main flow is chart -> input block -> unified
            # history section. ROUND-40: no fin_section either (the
            # money strip lives inside the input block).
            assert not hasattr(tab, "panels_section")
            assert not hasattr(tab, "fin_section")
            slaves = tab.right_inner.pack_slaves()
            seq = [tab.chart, tab.input_block, tab.history_section]
            idx = [slaves.index(w) for w in seq]
            assert idx == sorted(idx), idx
        finally:
            root.destroy()
    finally:
        _cleanup(fid)

def test_r16_panel_header_collapses():
    root, tab = _build("en", None)
    if tab is None:
        print("SKIP test_r16_panel_header_collapses (no display)")
        return
    try:
        # ROUND-24 SUPERSESSION: every collapsible summary panel is
        # removed (the last one, "procedures", went with the unified
        # table), so there are no panel headers to collapse -- the
        # collapse feature's absence IS the current spec.
        assert not hasattr(tab, "panel_texts")
        assert not hasattr(tab, "_panel_headers")
    finally:
        root.destroy()

def test_r16_panel_row_click_opens_detail():
    fid = _seed_patient("", "")
    try:
        _seed_payment(fid, "2026-11-01", "16", 50000, 80000)
        _seed_rx(fid, "fady", ["Amoxicillin"])
        # Round 23: a session row for the payment's date+tooth, so
        # the History tree carries the payment's money.
        conn = get_connection(); cur = conn.cursor()
        cur.execute("INSERT INTO procedures(patient_file,visit_date,tooth_number,procedure_done) VALUES(?,?,?,?)",
                    (fid, "2026-11-01", "16", "Root canal"))
        conn.commit(); conn.close()
        patient = {"file_number": fid, "full_name": "R16 Click Test", "mobile1": "", "birth_date_greg": "1990-01-01", "current_medications": "", "allergies": ""}
        root, tab = _build("en", patient)
        if tab is None:
            print("SKIP test_r16_panel_row_click_opens_detail (no display)")
            return
        try:
            tab.load(fid)
            root.update()
            # R23 supersedes the payments-PANEL row click: detail
            # migrated onto History rows; asserted via its handler.
            iid = tab.tree_history.get_children()[0]
            tab.tree_history.selection_set(iid)
            with mock.patch.object(_hist_r23.messagebox, "showinfo") as info:
                assert _hist_r23.show_history_payment_detail(tab) is True
                root.update()
            assert info.called, "history row detail opened no dialog"
            assert "Payment details" in info.call_args[0][0]
            assert "2026-11-01" in info.call_args[0][1]
            assert "50000" in info.call_args[0][1]
            # Round 22: the "rx" summary panel and its click-detail
            # no longer exist -- superseded by the full Rx section,
            # so the seeded Rx row is asserted on tree_hist instead
            # (doctor + drug in the row values).
            assert "Amoxicillin" in _rx_hist(tab) and "fady" in _rx_hist(tab)
        finally:
            root.destroy()
    finally:
        _cleanup(fid)
