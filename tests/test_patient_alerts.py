"""Job 4 (round 12): patient alerts.

When a patient is selected, a distinctive-colour strip shows on the
patient panel (clinical page AND patient form) when the patient has:
  (a) a drug allergy (patients.allergies) or current medication
      (patients.current_medications) -> RED strip;
  (b) an unpaid balance (patient_totals()["remaining"] > 0) -> AMBER strip.
A clean patient shows nothing.

Seeds three patients (allergy / balance / clean) and checks the pure
logic plus the shell's far-left Patient info panel, where the strip
lives since round 20 (it was on the clinical tab before). The
patient-form strip and the Add image button live in
test_patient_alerts_form.py (200-line split).
GUI tests skip gracefully when no display is available; run with
DISPLAY=:99 under Xvfb. Seeded rows are cleaned up.
"""
import tkinter as tk

from src.models.database import get_connection, init_db
from src.ui import patient_alerts
from src.ui.clinical import ClinicalTab
from src.ui.patient_info import PatientInfoPanel


def _stub_app(patient=None):
    class FakeApp:
        lang = "en"
        current_patient = patient
        current_user = "fady"
        current_role = "admin"

        def chart_teeth(self):
            return []

        def refresh_clinical(self):
            pass

        def on_teeth_select(self, teeth, typ):
            pass

        def print_pdf(self):
            pass

    return FakeApp()


def _seed(allergies="", meds="", balance=0.0):
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,father_name,grand_name,"
                "last_name,full_name,birth_date_greg,allergies,"
                "current_medications) VALUES(?,?,?,?,?,?,?,?)",
                ("Alert", "Father", "Grand", "Last",
                 "Alert Father Grand Last", "1990-05-15",
                 allergies, meds))
    fid = cur.lastrowid
    if balance:
        cur.execute("INSERT INTO financials(patient_file,total_cost,"
                    "paid_amount,remaining,visit_date) VALUES(?,?,?,?,?)",
                    (fid, balance, 0.0, balance, "2026-11-09"))
    conn.commit(); conn.close()
    return fid


def _row(fid):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM patients WHERE file_number=?", (fid,))
    row = dict(cur.fetchone())
    conn.close()
    return row


def _cleanup(fid):
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
        conn.commit(); conn.close()
    except Exception:
        pass


def test_alert_logic_allergy_meds_balance_clean():
    fid_a = _seed(allergies="Penicillin", meds="Metformin")
    fid_b = _seed(balance=500.0)
    fid_c = _seed()
    try:
        alerts = patient_alerts.patient_alerts(_row(fid_a))
        kinds = [k for k, _m in alerts]
        assert kinds == ["health", "health"], alerts
        assert "Penicillin" in alerts[0][1] and "Metformin" in alerts[1][1]
        alerts = patient_alerts.patient_alerts(_row(fid_b))
        assert [k for k, _m in alerts] == ["balance"], alerts
        assert "500.00" in alerts[0][1], alerts
        assert patient_alerts.patient_alerts(_row(fid_c)) == []
        assert patient_alerts.patient_alerts(None) == []
        # Arabic messages.
        alerts = patient_alerts.patient_alerts(_row(fid_a), lang="ar")
        assert "حساسية دوائية" in alerts[0][1]
        alerts = patient_alerts.patient_alerts(_row(fid_b), lang="ar")
        assert "رصيد غير مسدد" in alerts[0][1]
    finally:
        _cleanup(fid_a); _cleanup(fid_b); _cleanup(fid_c)


def test_alert_strip_shell_info_panel():
    """Round 20: the strip moved from the clinical tab into the
    shell's far-left Patient info panel (the single info display).
    The clinical tab must NOT carry a strip (or a name header)
    any more; the panel shows red for allergy, amber for balance,
    nothing for a clean patient."""
    fid_a = _seed(allergies="Penicillin")
    fid_b = _seed(balance=250.0)
    fid_c = _seed()
    try:
        root = tk.Tk()
    except tk.TclError:
        _cleanup(fid_a); _cleanup(fid_b); _cleanup(fid_c)
        print("SKIP test_alert_strip_shell_info_panel (no display)")
        return
    root.withdraw()
    try:
        app = _stub_app()
        tab = ClinicalTab(root, app)
        tab.pack()
        panel = PatientInfoPanel(root, app)
        panel.pack()
        root.update()
        assert not hasattr(tab, "alert_strip"), "clinical strip not removed"
        assert not hasattr(tab, "lbl_pat_name"), "clinical header not removed"
        assert hasattr(tab, "btn_add_image"), "Add image button missing"
        strip = panel.alert_strip
        # Allergy patient: red strip visible with the allergy named.
        panel.refresh(_row(fid_a))
        root.update()
        assert strip.winfo_manager() == "pack", "allergy strip not shown"
        assert "Penicillin" in strip.lbl_health.cget("text")
        assert strip.lbl_health.cget("bg") == patient_alerts.HEALTH_BG
        # Balance patient: amber strip, no red label.
        panel.refresh(_row(fid_b))
        root.update()
        assert strip.winfo_manager() == "pack", "balance strip not shown"
        assert "250.00" in strip.lbl_balance.cget("text")
        assert strip.lbl_balance.cget("bg") == patient_alerts.BALANCE_BG
        # Clean patient: strip hidden.
        panel.refresh(_row(fid_c))
        root.update()
        assert strip.winfo_manager() == "", "clean patient shows strip"
    finally:
        root.destroy()
        _cleanup(fid_a); _cleanup(fid_b); _cleanup(fid_c)
