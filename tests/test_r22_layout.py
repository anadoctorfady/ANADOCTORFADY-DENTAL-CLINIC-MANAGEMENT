"""Round 22 regression: the pinned patient header + moved panels.

Owner redesign (2026-11-16), superseding the round-21 layout
pinned by test_r21_layout_red.py:
A. The Clinical tab opens with a PINNED HEADER (personal info +
   Health lines + both alert strips + Edit/Delete/Refer) packed
   OUTSIDE the scroll canvas: still mapped at the same y after
   the main canvas scrolls to the bottom (the chart scrolls
   away). Debtor + allergy patient: red name, red Diseases /
   Allergies lines (meds line NOT red), both strips visible.
   Clean patient: strips hidden, no reds. No patient: header
   cleared to a neutral placeholder, buttons disabled.
B. Main scroll order: chart -> input tables -> History -> panels
   -> finance -> scans. (Round 23 supersession: the Recent
   Payments panel was removed; only Therapeutic Procedures
   remains -- panel-set coverage lives in test_r22_shell_rx.py.)
C. The shell's far-left column keeps ONLY search + list + the
   Prescriptions section (app.rx_host): compose + history +
   Print reachable by scrolling at 1380x820, EN + AR.
Full-App tests run only on an isolated gate copy
(ANADOCTORFADY_DATA_DIR set); GUI parts skip with no display.
Seeded rows are cleaned up."""
import os
import tkinter as tk

from src.config.theme import debt_red
from src.models.database import get_connection
from src.models.finance import patient_totals
from tests.test_r18_info_panel_visible import _display_available, _login


def _ready():
    if not os.environ.get("ANADOCTORFADY_DATA_DIR"):
        print("SKIP (not an isolated gate copy)"); return False
    if not _display_available():
        print("SKIP (no display)"); return False
    return True


def _boot(geo="1380x1000"):
    from src.ui.shell import App
    from src.utils.auth import hash_pw
    conn = get_connection()
    conn.execute("UPDATE users SET password_hash=? WHERE username='fady'",
                 (hash_pw("1234"),))
    conn.commit(); conn.close()
    app = App()
    _login(app)
    app.geometry(geo); app.update()
    return app


def _chain(w):
    out = []
    while w is not None:
        out.append(w); w = w.master
    return out


def _inside(app, w):
    top = w.winfo_rooty() - app.winfo_rooty()
    left = w.winfo_rootx() - app.winfo_rootx()
    return (0 <= top and top + w.winfo_height() <= app.winfo_height()
            and 0 <= left and left + w.winfo_width() <= app.winfo_width())


def _seed(allergies="", diseases="", meds="", total=0.0, paid=0.0):
    from src.models.database import init_db
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,father_name,grand_name,"
                "last_name,full_name,birth_date_greg,allergies,diseases,"
                "current_medications) VALUES(?,?,?,?,?,?,?,?,?)",
                ("R22", "Father", "Grand", "Last", "R22 Father Grand Last",
                 "1990-05-15", allergies, diseases, meds))
    fid = cur.lastrowid
    if total:
        cur.execute("INSERT INTO financials(patient_file,total_cost,"
                    "paid_amount,remaining,visit_date) VALUES(?,?,?,?,?)",
                    (fid, total, paid, total - paid, "2026-11-09"))
    conn.commit(); conn.close()
    return fid


def _cleanup(*fids):
    try:
        conn = get_connection(); cur = conn.cursor()
        for fid in fids:
            cur.execute("DELETE FROM financials WHERE patient_file=?", (fid,))
            cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
        conn.commit(); conn.close()
    except Exception:
        pass


def _debtor_fid():
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT file_number FROM patients WHERE deleted=0")
    fids = [r[0] for r in cur.fetchall()]; conn.close()
    for fid in fids:
        if patient_totals(fid)["remaining"] > 0:
            return fid
    return None


def test_pinned_header_stays_after_scroll_to_bottom():
    if not _ready():
        return
    app = _boot("1380x1000")
    try:
        tab = app.clinical
        hdr = tab.header_panel
        assert hdr is app.info_panel  # shell refresh target
        assert hdr.master is tab  # packed in the tab, NOT the canvas
        assert tab.main_canvas not in _chain(hdr)
        fid = _debtor_fid()
        assert fid is not None, "gate copy has no debtor patient"
        app.select_patient(fid); app.update()
        # Worst case (both strips visible): still compact. R55
        # re-pin (195 -> 230): the 3-row strip's cells wrap at this
        # 1380px width (narrower than the 1920 gallery size), and
        # the alert banners below it are conditional; 216 measured
        # on the fresh fixture copy. The header stays pinned outside
        # the scroll canvas, which is what this test guards.
        assert hdr.winfo_height() <= 230, hdr.winfo_height()
        y0 = hdr.winfo_rooty()
        tab.main_canvas.yview_moveto(1.0); app.update()
        assert tab.main_canvas.yview()[0] > 0.5  # really scrolled
        assert hdr.winfo_ismapped() == 1
        assert hdr.winfo_rooty() == y0, (y0, hdr.winfo_rooty())
        assert _inside(app, hdr)
        # The chart scrolled away above the viewport.
        assert tab.chart.winfo_rooty() + tab.chart.winfo_height() \
            <= hdr.winfo_rooty()
    finally:
        app.destroy()


def test_header_content_debtor_allergy_and_clean():
    if not _ready():
        return
    fid_alert = _seed(allergies="Penicillin", diseases="Diabetes",
                      meds="Metformin", total=1000.0, paid=250.0)
    fid_clean = _seed()
    app = _boot("1380x1000")
    try:
        hdr = app.info_panel
        # Round 55: the name sits on a pastel strip cell in BOTH themes, so the debtor red is ALWAYS the light-mode (dark) red -- never the dark-mode #F87171 (~2:1 on pastel).
        red = debt_red(False)
        app.select_patient(fid_alert); app.update()
        assert hdr._name_lbl.cget("fg") == red
        # Round 55: the file number rides INSIDE the name cell ("Name: …  #fid"); no separate _file_lbl now.
        assert f"#{fid_alert}" in hdr._name_lbl.cget("text")
        assert hdr._health_lbls["diseases"].cget("fg") == red
        assert hdr._health_lbls["allergies"].cget("fg") == red
        assert hdr._health_lbls["current_medications"].cget("fg") != red
        strip = hdr.alert_strip
        assert strip.winfo_ismapped() == 1
        assert "Penicillin" in strip.lbl_health.cget("text")
        assert "750.00" in strip.lbl_balance.cget("text")
        assert str(hdr.edit_btn["state"]) == "normal"
        app.select_patient(fid_clean); app.update()
        assert hdr._name_lbl.cget("fg") != red
        assert hdr._health_lbls["allergies"].cget("fg") != red
        assert strip.winfo_manager() == ""  # clean patient: no strips
        assert strip.winfo_ismapped() == 0
    finally:
        app.destroy()
        _cleanup(fid_alert, fid_clean)


def test_no_patient_clears_header():
    if not _ready():
        return
    fid = _seed(allergies="Penicillin", total=500.0, paid=0.0)
    app = _boot("1380x1000")
    try:
        hdr = app.info_panel
        app.select_patient(fid); app.update()
        assert "R22" in hdr._name_lbl.cget("text")
        # The real new-patient path clears the patient everywhere.
        dlg = app.new_patient(); app.update()
        try:
            assert app.current_patient is None
            assert "R22" not in hdr.info_text()
            # Round 55: no separate _file_lbl -- cleared header shows the title in the name cell, no file no.
            assert "#" not in hdr._name_lbl.cget("text")
            for lbl in hdr._health_lbls.values():
                assert lbl.cget("text") == ""
            assert hdr.alert_strip.winfo_ismapped() == 0
            for btn in (hdr.edit_btn, hdr.delete_btn, hdr.refer_btn):
                assert str(btn["state"]) == "disabled"
        finally:
            if dlg is not None:
                try: dlg.destroy()
                except Exception: pass
    finally:
        app.destroy()
        _cleanup(fid)
