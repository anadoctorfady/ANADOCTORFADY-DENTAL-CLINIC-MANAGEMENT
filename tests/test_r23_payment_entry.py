"""Round 23, item 7 (BUG): payment entry refused legitimate saves --
boxes measured against CUMULATIVE totals, Tooth box never read.
R23 fix: per-tooth buckets + delta rule. ROUND-24 SUPERSESSION:
the unified session table + session_money replace the bucket/delta
entry. These tests keep the R23 scenarios + endpoint totals via
the R24 entries; the model bucket test is unchanged. Isolated DB.
ROUND-38 SUPERSESSION: the finance entry is the standalone PAYMENT
entry — NO Tooth box, NO Total box; chart clicks sync the SESSION
tooth box only; the general payment test is its native case.
ROUND-40 RE-PIN: the payment entry zone is REMOVED — ONE payment
place; overpayment SPLITS to an advance row, not a refusal."""
import tkinter as tk
from src.models.database import get_connection, save_financial
from src.models.finance import patient_totals
from src.models.finance_totals import normalize_tooth_key, patient_tooth_totals
from tests.test_payments_e2e import (TODAY, _seed_users, _seed_patient,
                                     _rows, _cleanup, _patch_msgs,
                                     _build_clinical, _set)
EARLIER = "2026-11-10"

def _detail(fid):
    conn = get_connection(); out = [tuple(r) for r in conn.execute("SELECT tooth_number,total_cost,paid_amount FROM financials WHERE patient_file=? ORDER BY id", (fid,))]; conn.close(); return out

DAY2 = "2026-11-11"

def _save_session(tab, tooth, total, paid, date=DAY2):
    """A session through the REAL unified entry + Save session."""
    from src.ui import clinical_session_entry as _entry
    for w, txt in ((tab.txt_complaint, "Pain"), (tab.txt_sym, "Sharp"),
                   (tab.txt_diagnosis, "Caries"), (tab.txt_procedure, "Filling")):
        w.delete("1.0", tk.END); w.insert("1.0", txt)
    tab.e_sess_date.delete(0, tk.END); tab.e_sess_date.insert(0, date)
    tab.e_sess_tooth.delete(0, tk.END)
    if tooth:
        tab.e_sess_tooth.insert(0, tooth)
    _entry.set_money(tab, total, paid)
    tab.btn_save_visit.invoke()

def test_a_partial_payment_toward_existing_tooth():
    """(a) Tooth 16: 400,000/250,000 earlier + tooth 11 fully paid.
    A further 100,000 toward 16 as a NEW session's Paid must SAVE."""
    _seed_users(); fid = _seed_patient("R23A")
    try:
        save_financial(fid, "16", 400000, 250000, EARLIER, doctor="doc_x", entered_by="doc_x"); save_financial(fid, "11", 200000, 200000, EARLIER, doctor="doc_x", entered_by="doc_x")
        caps, restore = _patch_msgs(); root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None: print("SKIP (a) no display"); restore(); return
        try:
            _save_session(tab, "16", 0, 100000); root.update_idletasks()
            assert not caps["error"], caps["error"]
            assert _detail(fid)[-1] == ("16", 0.0, 100000.0), _detail(fid)
            assert patient_tooth_totals(fid, "16") == {"total": 400000.0, "paid": 350000.0, "remaining": 50000.0}
            assert patient_tooth_totals(fid, "11") == {"total": 200000.0, "paid": 200000.0, "remaining": 0.0}
            assert patient_totals(fid) == {"total": 600000.0, "paid": 550000.0, "remaining": 50000.0}
        finally: root.destroy(); restore()
    finally: _cleanup(fid)

def test_b_new_tooth_own_total_saves():
    """(b) NEW tooth 36 session (300,000/100,000) while tooth 16's
    balance exists: its OWN amounts must SAVE (chart-selected)."""
    _seed_users(); fid = _seed_patient("R23B")
    try:
        save_financial(fid, "16", 400000, 250000, EARLIER, doctor="doc_x", entered_by="doc_x")
        caps, restore = _patch_msgs(); root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None: print("SKIP (b) no display"); restore(); return
        try:
            tab.chart.toggle("36"); root.update_idletasks()
            assert tab.e_sess_tooth.get() == "36"  # R38: no finance tooth box anymore
            assert tab.e_sess_paid.get() == "0"  # R40: the ONE entry's Paid
            _save_session(tab, "36", 300000, 100000); root.update_idletasks()
            assert not caps["error"], caps["error"]
            assert _detail(fid)[-1] == ("36", 300000.0, 100000.0), _detail(fid)
            assert patient_tooth_totals(fid, "36") == {"total": 300000.0, "paid": 100000.0, "remaining": 200000.0}
            assert patient_tooth_totals(fid, "16") == {"total": 400000.0, "paid": 250000.0, "remaining": 150000.0}
            assert patient_totals(fid) == {"total": 700000.0, "paid": 350000.0, "remaining": 350000.0}
        finally: root.destroy(); restore()
    finally: _cleanup(fid)

def test_c_same_tooth_increase_saves_delta():
    """(c) Same tooth continuation: a new session on tooth 16 with
    Total 100,000 / Paid 100,000 lands exactly the row the old delta
    flow saved; totals 500,000/350,000."""
    _seed_users(); fid = _seed_patient("R23C")
    try:
        save_financial(fid, "16", 400000, 250000, TODAY, doctor="doc_x", entered_by="doc_x")
        caps, restore = _patch_msgs(); root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None: print("SKIP (c) no display"); restore(); return
        try:
            _save_session(tab, "16", 100000, 100000); root.update_idletasks()
            assert not caps["error"], caps["error"]
            assert _detail(fid)[-1] == ("16", 100000.0, 100000.0), _detail(fid)
            assert patient_totals(fid) == {"total": 500000.0, "paid": 350000.0, "remaining": 150000.0}
        finally: root.destroy(); restore()
    finally: _cleanup(fid)

def test_unchanged_resave_creates_no_row():
    """Anti-doubling, R40 form: the ONE entry starts 0/0, so an
    untouched Save shows the session gate error, adds NO row."""
    _seed_users(); fid = _seed_patient("R23NoDup")
    try:
        save_financial(fid, "16", 400000, 250000, EARLIER, doctor="doc_x", entered_by="doc_x")
        caps, restore = _patch_msgs(); root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None: print("SKIP no-dup no display"); restore(); return
        try:
            from src.ui import clinical_session_entry as _entry
            assert _entry.get_money(tab) == (0.0, 0.0)
            tab.btn_save_visit.invoke(); root.update_idletasks()
            assert caps["error"], "untouched entry must show the session gate"
            assert _rows(fid) == 1 and patient_totals(fid)["paid"] == 250000.0
        finally: root.destroy(); restore()
    finally: _cleanup(fid)

def test_overpayment_splits_to_advance_bilingually():
    """ROUND-40 RE-PIN (was test_overpayment_refused_bilingually):
    Paid 400,000 / Total 100,000 vs a 250,000 balance (cap 350,000)
    SPLITS — session absorbs 350,000, excess 50,000 = standalone
    advance; split info in EN+AR; totals 700k/750k/-50k (credit)."""
    _seed_users()
    caps, restore = _patch_msgs()
    try:
        for lang in ("en", "ar"):
            _seed_users()  # per-lang cleanup below deletes them again
            fid2 = _seed_patient("R23Dec" + lang)
            try:
                save_financial(fid2, "16", 600000, 350000, EARLIER, doctor="doc_x", entered_by="doc_x")
                root, tab = _build_clinical("doc_x", "doctor", fid2, lang)
                if tab is None: print("SKIP overpay no display"); return
                try:
                    _save_session(tab, "16", 100000, 400000); root.update_idletasks()
                    assert not caps["error"], (lang, caps)
                    assert caps["info"] and "50000" in caps["info"][-1][1], caps["info"]
                    assert _rows(fid2) == 3  # seed + session part + standalone excess
                    assert _detail(fid2)[1] == ("16", 100000.0, 350000.0), _detail(fid2)
                    assert _detail(fid2)[2] == ("", 0.0, 50000.0), _detail(fid2)
                    assert patient_totals(fid2) == {"total": 700000.0, "paid": 750000.0,
                                                    "remaining": -50000.0}
                    conn = get_connection()
                    n = conn.execute("SELECT COUNT(*) FROM diagnoses WHERE patient_file=?", (fid2,)).fetchone()[0]
                    conn.close()
                    assert n == 1, "split save must keep the clinical rows"
                    caps["info"].clear()
                finally: root.destroy()
            finally: _cleanup(fid2)
    finally: restore()

def test_general_payment_empty_tooth_saves():
    """General payment via the ONE entry's PURE ADVANCE route
    (no tooth/text, Total 0): a ''-tooth standalone row."""
    _seed_users(); fid = _seed_patient("R23Gen")
    try:
        save_financial(fid, "16", 400000, 250000, EARLIER, doctor="doc_x", entered_by="doc_x")
        caps, restore = _patch_msgs(); root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None: print("SKIP general no display"); restore(); return
        try:
            assert not hasattr(tab, "e_fin_tooth")
            tab.app.chart_teeth = lambda: []  # advance: nothing selected
            from src.ui import clinical_session_entry as _entry
            assert _entry.get_money(tab) == (0.0, 0.0)
            _set(tab, 100000, "doc_x"); tab.btn_save_visit.invoke(); root.update_idletasks()
            assert not caps["error"], caps["error"]
            assert _detail(fid)[-1] == ("", 0.0, 100000.0), _detail(fid)
            assert patient_tooth_totals(fid, "") == {"total": 0.0, "paid": 100000.0, "remaining": -100000.0}
            assert patient_totals(fid) == {"total": 400000.0, "paid": 350000.0, "remaining": 50000.0}
        finally: root.destroy(); restore()
    finally: _cleanup(fid)

def test_chart_click_syncs_tooth_boxes():
    """R40: chart clicks sync the SESSION tooth box only, and
    never refill the session Paid box."""
    _seed_users(); fid = _seed_patient("R23Chart")
    try:
        save_financial(fid, "16", 400000, 250000, EARLIER, doctor="doc_x", entered_by="doc_x"); save_financial(fid, "36", 300000, 100000, EARLIER, doctor="doc_x", entered_by="doc_x")
        root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None: print("SKIP chart sync no display"); return
        try:
            assert not hasattr(tab, "e_fin_tooth")
            tab.chart.toggle("16"); root.update_idletasks()
            assert tab.e_sess_tooth.get() == "16"
            assert tab.e_sess_paid.get() == "0"
            tab.chart.toggle("36"); root.update_idletasks()
            assert tab.e_sess_tooth.get() == "16,36"
            tab.chart.toggle("16"); root.update_idletasks()
            assert tab.e_sess_tooth.get() == "36"
        finally: root.destroy()
    finally: _cleanup(fid)

def test_tooth_totals_model_buckets():
    """Model: buckets sum independently; stored '36,16' normalizes to
    the '16,36' bucket; '' sums only general rows; patient_totals is
    the sum over all buckets."""
    _seed_users(); fid = _seed_patient("R23Model")
    try:
        save_financial(fid, "16", 400000, 250000, EARLIER); save_financial(fid, "16", 0, 50000, EARLIER)
        save_financial(fid, "36,16", 90000, 90000, EARLIER); save_financial(fid, "", 0, 20000, EARLIER)
        assert normalize_tooth_key("36, 16") == "16,36" and normalize_tooth_key("") == ""
        assert patient_tooth_totals(fid, "16") == {"total": 400000.0, "paid": 300000.0, "remaining": 100000.0}
        assert patient_tooth_totals(fid, "16,36") == {"total": 90000.0, "paid": 90000.0, "remaining": 0.0}
        assert patient_tooth_totals(fid, "") == {"total": 0.0, "paid": 20000.0, "remaining": -20000.0}
        assert patient_totals(fid) == {"total": 490000.0, "paid": 410000.0, "remaining": 80000.0}
    finally: _cleanup(fid)
