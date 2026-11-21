"""Round 23, item 7 (BUG): payment entry refused legitimate saves --
load_costs/add_fin measured the boxes against the patient's CUMULATIVE
totals across ALL teeth and the Tooth box was never read. R23 fix:
per-tooth buckets + delta rule. ROUND-24 SUPERSESSION (items 2+3):
the bucket/delta entry is REPLACED by the unified session table +
session_money -- a session's Paid may exceed its own Total up to the
patient's outstanding balance; the finance boxes are one standalone
payment under the same rule. These tests keep the R23 scenarios and
endpoint totals via the R24 entries; the model bucket test is
unchanged (buckets still exist in the data layer). Isolated DB.
ROUND-38 SUPERSESSION: the finance entry is the standalone PAYMENT
entry — NO Tooth box, NO Total box; chart clicks sync the SESSION
tooth box only; the general payment test is its native case."""
import tkinter as tk
from src.models.database import get_connection, save_financial
from src.models.finance import patient_totals
from src.models.finance_totals import normalize_tooth_key, patient_tooth_totals
from src.ui import clinical_finance as _fin
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
            assert tab.e_paid.get() == "0"
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
    """Anti-doubling, R24 form: boxes start 0/0 after load, so an
    untouched Add Payment shows the no-change info, adds NO row."""
    _seed_users(); fid = _seed_patient("R23NoDup")
    try:
        save_financial(fid, "16", 400000, 250000, EARLIER, doctor="doc_x", entered_by="doc_x")
        caps, restore = _patch_msgs(); root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None: print("SKIP no-dup no display"); restore(); return
        try:
            assert tab.e_paid.get() == "0"
            tab.add_fin(); root.update_idletasks()
            assert caps["info"], "untouched entry must show the no-change info"
            assert _rows(fid) == 1 and patient_totals(fid)["paid"] == 250000.0
        finally: root.destroy(); restore()
    finally: _cleanup(fid)

def test_overpayment_refused_bilingually():
    """ROUND-24 SUPERSESSION of test_per_tooth_decrease_refused_
    bilingually: decreases are inexpressible now (history is never
    rewritten by entry); the refusal that remains is the genuine
    overpayment -- session Paid 400,000 with Total 100,000 against a
    250,000 balance (cap 350,000) -- refused in EN and AR, the cap
    stated, NOTHING saved (no clinical rows either)."""
    _seed_users(); fid = _seed_patient("R23Dec")
    try:
        save_financial(fid, "16", 600000, 350000, EARLIER, doctor="doc_x", entered_by="doc_x")
        caps, restore = _patch_msgs()
        try:
            for lang, needle in (("en", "maximum"), ("ar", "الحد الأقصى")):
                root, tab = _build_clinical("doc_x", "doctor", fid, lang)
                if tab is None: print("SKIP overpay no display"); return
                try:
                    _save_session(tab, "16", 100000, 400000); root.update_idletasks()
                    assert caps["error"], f"no refusal in {lang}"
                    msg = caps["error"][-1][1]
                    assert needle in msg and "350000" in msg, (lang, msg)
                    assert _rows(fid) == 1 and patient_totals(fid)["paid"] == 350000.0
                    conn = get_connection()
                    n = conn.execute("SELECT COUNT(*) FROM diagnoses WHERE patient_file=?", (fid,)).fetchone()[0]
                    conn.close()
                    assert n == 0, "refused save left clinical rows behind"
                finally: root.destroy()
        finally: restore()
    finally: _cleanup(fid)

def test_general_payment_empty_tooth_saves():
    """General payment through the PAYMENT entry: 100,000 saves a
    ''-tooth standalone row; totals rise by the payment only.
    ROUND-38: the entry's native case (no Tooth box at all)."""
    _seed_users(); fid = _seed_patient("R23Gen")
    try:
        save_financial(fid, "16", 400000, 250000, EARLIER, doctor="doc_x", entered_by="doc_x")
        caps, restore = _patch_msgs(); root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None: print("SKIP general no display"); restore(); return
        try:
            assert not hasattr(tab, "e_fin_tooth")
            assert tab.e_paid.get() == "0"
            _set(tab, 100000, "doc_x"); tab.add_fin(); root.update_idletasks()
            assert not caps["error"], caps["error"]
            assert _detail(fid)[-1] == ("", 0.0, 100000.0), _detail(fid)
            assert patient_tooth_totals(fid, "") == {"total": 0.0, "paid": 100000.0, "remaining": -100000.0}
            assert patient_totals(fid) == {"total": 400000.0, "paid": 350000.0, "remaining": 50000.0}
        finally: root.destroy(); restore()
    finally: _cleanup(fid)

def test_chart_click_syncs_tooth_boxes():
    """ROUND-38: chart clicks sync the SESSION tooth box only —
    the payment entry has none — and never refill the Amount box."""
    _seed_users(); fid = _seed_patient("R23Chart")
    try:
        save_financial(fid, "16", 400000, 250000, EARLIER, doctor="doc_x", entered_by="doc_x"); save_financial(fid, "36", 300000, 100000, EARLIER, doctor="doc_x", entered_by="doc_x")
        root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None: print("SKIP chart sync no display"); return
        try:
            assert not hasattr(tab, "e_fin_tooth")
            tab.chart.toggle("16"); root.update_idletasks()
            assert tab.e_sess_tooth.get() == "16"
            assert tab.e_paid.get() == "0"
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
