"""Round 15 clinical panels: diseases / medicines / allergies,
payments, prescriptions from the live record, bilingual empty
states; seeded rows deleted afterwards; GUI skips w/o display.
R22: Health lives in the PINNED HEADER (tab.header_panel); the
"rx" panel is superseded by tab.rx_section.tree_hist. R23: the
Recent Payments panel was REMOVED (History carries per-session
money) -- GUI tests read payments from tab.tree_fin; DATA tests
unchanged. ROUND-24 SUPERSESSION (items 2+6): the Therapeutic
Procedures panel was REMOVED too -- no summary panels are built;
procedures live in the unified session tree."""
import tkinter as tk
from src.models.database import get_connection, init_db
from src.models.prescriptions import save_prescription
from src.ui.clinical import ClinicalTab
from src.ui.clinical_panels import (format_meds, format_payments, format_rx, last_payments,
                                    meds_allergies, recent_prescriptions)

def _seed_patient(meds="", allergies=""):
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name,current_medications,allergies) VALUES(?,?,?,?)", ("R15", "R15 Panel Test", meds, allergies))
    fid = cur.lastrowid; conn.commit(); conn.close()
    return fid

def _seed_payment(fid, date, tooth, paid, total):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO financials(patient_file,tooth_number,total_cost,paid_amount,remaining,visit_date,total_syp,paid_syp,remaining_syp) VALUES(?,?,?,?,?,?,?,?,?)", (fid, tooth, total, paid, total - paid, date, total, paid, total - paid))
    rid = cur.lastrowid; conn.commit(); conn.close()
    return rid

def _seed_rx(fid, doctor, drugs):
    items = [{"generic": g, "brand": "", "dose": "500 mg", "frequency": "x2", "duration_days": "5", "instructions": ""} for g in drugs]
    return save_prescription(fid, items, doctor=doctor)

def _cleanup(fid):
    conn = get_connection(); cur = conn.cursor()
    for sql, key in (("DELETE FROM prescription_items WHERE prescription_id IN (SELECT id FROM prescriptions WHERE patient_file=?)", fid),
                     ("DELETE FROM prescriptions WHERE patient_file=?", fid), ("DELETE FROM financials WHERE patient_file=?", fid),
                     ("DELETE FROM patients WHERE file_number=?", fid)):
        cur.execute(sql, (key,))
    conn.commit(); conn.close()

def test_panels_data_seeded_patient():
    fid = _seed_patient("Amoxicillin 500 mg, Paracetamol", "Penicillin")
    try:
        _seed_payment(fid, "2026-11-01", "16", 50000, 80000)
        _seed_payment(fid, "2026-11-03", "11", 30000, 30000)
        _seed_payment(fid, "2026-11-05", "", 10000, 10000)
        pid = _seed_rx(fid, "fady", ["Amoxicillin", "Ibuprofen"])
        ma = meds_allergies({"current_medications": "Amoxicillin 500 mg, Paracetamol", "allergies": "Penicillin"})
        assert ma == {"medicines": ["Amoxicillin 500 mg", "Paracetamol"], "allergies": ["Penicillin"]}
        pays = last_payments(fid)
        assert len(pays) == 3, pays
        assert pays[0]["date"] == "2026-11-05" and pays[0]["paid"] == 10000
        assert pays[1]["tooth"] == "11" and pays[1]["paid"] == 30000
        lines = format_payments(pays, "en")
        assert "2026-11-03" in lines[1] and "Tooth 11" in lines[1] and "30000" in lines[1]
        assert "Visit" in lines[0]  # no tooth recorded -> "Visit"
        rxs = recent_prescriptions(fid)
        assert len(rxs) == 1 and rxs[0]["id"] == pid
        assert rxs[0]["drugs"] == ["Amoxicillin", "Ibuprofen"]
        assert "Ibuprofen" in format_rx(rxs, "en")[0] and "fady" in format_rx(rxs, "en")[0]
        # Limit: 3 more payments -> only the 4 most recent are shown.
        for _ in range(3):
            _seed_payment(fid, "2026-11-06", "21", 1000, 1000)
        assert len(last_payments(fid)) == 4
    finally:
        _cleanup(fid)

def test_panels_data_empty_patient_and_nulls():
    fid = _seed_patient("", "")
    try:
        assert meds_allergies({"current_medications": None, "allergies": None}) == {"medicines": [], "allergies": []}
        assert meds_allergies(None) == {"medicines": [], "allergies": []}
        assert meds_allergies({}) == {"medicines": [], "allergies": []}
        assert last_payments(fid) == [] and recent_prescriptions(fid) == []
        assert last_payments(None) == [] and recent_prescriptions(None) == []
        assert format_payments([], "en") == ["No payments yet"]
        assert format_rx([], "ar") == ["لا توجد وصفات بعد"]
        assert format_meds({"medicines": [], "allergies": []}, "en") == ["Medicines: None", "Allergies: None"]
        assert format_meds({"medicines": ["Aspirin"], "allergies": []}, "ar")[1].startswith("الحساسية:")
    finally:
        _cleanup(fid)

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
    root.withdraw()
    tab = ClinicalTab(root, _FakeApp(lang, patient))
    tab.pack()
    root.update_idletasks()
    return root, tab

def _panel_text(tab, key):
    return tab.panel_texts[key].get("1.0", tk.END)

def _health(tab, key):
    return tab.header_panel._health_lbls[key].cget("text")

def _rx_hist(tab):
    tree = tab.rx_section.tree_hist
    return " ".join(str(v) for i in tree.get_children() for v in tree.item(i, "values"))

def test_panels_gui_seeded_patient():
    fid = _seed_patient("Amoxicillin 500 mg", "Penicillin")
    try:
        _seed_payment(fid, "2026-11-01", "16", 50000, 80000)
        _seed_rx(fid, "fady", ["Amoxicillin"])
        patient = {"file_number": fid, "full_name": "R15 Panel Test", "mobile1": "", "birth_date_greg": "1990-01-01", "current_medications": "Amoxicillin 500 mg", "allergies": "Penicillin"}
        root, tab = _build("en", patient)
        if tab is None:
            print("SKIP test_panels_gui_seeded_patient (no display)")
            return
        try:
            tab.load(fid)
            root.update_idletasks()
            # ROUND-24 SUPERSESSION: NO summary panels are built
            # (procedures rows live in the unified tree).
            assert not hasattr(tab, "panel_texts")
            assert not hasattr(tab, "panel_frames")
            assert tab.tree_history.get_children() == ()
            # Health content moved to the pinned header (was "meds").
            assert "Amoxicillin 500 mg" in _health(tab, "current_medications")
            assert "Penicillin" in _health(tab, "allergies")
            assert "Amoxicillin 500 mg" in tab.header_panel.info_text()
            # R23 supersedes the payments-panel assert: payment in tree_fin.
            fin = " ".join(str(v) for i in tab.tree_fin.get_children() for v in tab.tree_fin.item(i, "values"))
            assert "2026-11-01" in fin and "50000" in fin, fin
            # The "rx" summary panel is superseded by the Rx section.
            assert "Amoxicillin" in _rx_hist(tab) and "fady" in _rx_hist(tab)
        finally:
            root.destroy()
    finally:
        _cleanup(fid)

def test_panels_gui_empty_patient_and_arabic():
    fid = _seed_patient("", "")
    try:
        patient = {"file_number": fid, "full_name": "R15 Empty", "mobile1": "", "birth_date_greg": "1990-01-01", "current_medications": "", "allergies": ""}
        root, tab = _build("en", patient)
        if tab is None:
            print("SKIP test_panels_gui_empty_patient (no display)")
            return
        try:
            tab.load(fid)
            root.update_idletasks()
            # R23/R24: empty state = EMPTY trees (panels removed).
            assert not tab.tree_fin.get_children()
            assert not tab.tree_history.get_children()
            assert not hasattr(tab, "panel_texts")
            # Round 22: empty Health lines show "—" in the header.
            for key in ("diseases", "current_medications", "allergies"):
                assert "—" in _health(tab, key), key
            assert not tab.rx_section.tree_hist.get_children()
        finally:
            root.destroy()
        # Arabic empty states (same patient, Arabic UI).
        root, tab = _build("ar", patient)
        if tab is None:
            print("SKIP test_panels_gui_arabic (no display)")
            return
        try:
            tab.load(fid)
            root.update_idletasks()
            # R23: same empty-tree supersession in AR (was panel text).
            assert not tab.tree_fin.get_children()
            assert not tab.tree_history.get_children()
            # Arabic header labels + the same "—" placeholder.
            assert _health(tab, "diseases").startswith("الأمراض")
            for key in ("diseases", "current_medications", "allergies"):
                assert "—" in _health(tab, key), key
            assert not tab.rx_section.tree_hist.get_children()
        finally:
            root.destroy()
    finally:
        _cleanup(fid)

def test_panels_gui_no_patient():
    root, tab = _build("en", None)
    if tab is None:
        print("SKIP test_panels_gui_no_patient (no display)")
        return
    try:
        # ROUND-24 SUPERSESSION: no panels are built; the header
        # keeps its placeholder and the unified tree is empty.
        assert not hasattr(tab, "panel_texts")
        assert tab.tree_history.get_children() == ()
        assert tab.header_panel._name_lbl.cget("text") == "Patient info"
    finally:
        root.destroy()
