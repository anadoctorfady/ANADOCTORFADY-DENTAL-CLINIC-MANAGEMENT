"""Round 23 (item 6): currencies end-to-end — the owner's LIVE defect
that a payment beyond SYP/USD (his example: Swedish krona, SEK) never
appeared in the financial calculations. Pre-fix reproductions (gate
copy, base SYP): SEK 1,000/600 @ 1,300 printed on the invoice as the
CONVERTED 780,000 labelled SYP (invoice used paid_syp + base code);
the report folded mixed rows raw under the FIRST row's currency
(500,000 SYP + 1,000 SEK = "501,000.00 SYP"); a foreign row with NO
saved rate (exchange_rate NULL, synced/legacy shape) was folded RAW
into base totals by every COALESCE(total_syp,total_cost) sum (500 SEK
became +500 SYP in flexible_totals). Seeded via the real models."""
import shutil, subprocess, tempfile
from datetime import date
from pathlib import Path
from src.models.database import get_connection, init_db, save_financial
from src.models.currency import save_rate
from src.models.finance import patient_totals
from src.models.finance_currency import (currencies_present,
    doctor_income_currency, totals_for_currency)
from src.models.finance_totals import flexible_totals, unconverted_totals
TODAY = date.today().isoformat()
RATE = 1300.0  # SYP per 1 SEK
DOC = "r23doc"
TMP = Path(tempfile.mkdtemp(prefix="r23_cur_"))
def _pdf_text(path):
    if not shutil.which("pdftotext"):
        print("SKIP pdf-text check (no pdftotext)"); return None
    r = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return r.stdout
def _patient(name):
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name) VALUES(?,?)", (name, name + " Patient"))
    fid = cur.lastrowid; conn.commit(); conn.close(); return fid
def _cleanup(*fids):
    conn = get_connection(); cur = conn.cursor()
    for fid in fids:
        cur.execute("DELETE FROM financials WHERE patient_file=?", (fid,))
        cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    cur.execute("DELETE FROM exchange_rates WHERE from_currency='SEK'")
    conn.commit(); conn.close()
def _seed_sek(fid, total=1000, paid=600):
    save_rate(TODAY, RATE, "SEK", "SYP")
    save_financial(fid, "16", total, paid, TODAY, currency="SEK", rate=RATE, rate_date=TODAY, doctor=DOC, entered_by=DOC)
def test_sek_appears_in_finance_per_currency_data():
    before = totals_for_currency("SEK", TODAY, TODAY)
    fid = _patient("R23SEK")
    try:
        _seed_sek(fid)
        assert "SEK" in currencies_present()
        sek = totals_for_currency("SEK", TODAY, TODAY)
        assert sek["total"] - before["total"] == 1000.0
        assert sek["total_income"] - before["total_income"] == 600.0
        assert sek["total_debts"] - before["total_debts"] == 400.0
        doc = doctor_income_currency(DOC, "SEK", TODAY, TODAY)
        assert (doc["total"], doc["paid"], doc["remaining"]) == (1000.0, 600.0, 400.0)
        # Converted base view still counts it -- at its OWN rate.
        assert patient_totals(fid) == {"total": 1000.0 * RATE, "paid": 600.0 * RATE, "remaining": 400.0 * RATE}
    finally: _cleanup(fid)
def test_sek_invoice_is_raw_sek_no_conversion():
    from src.reports.invoice_pdf import build_invoice_pdf, invoice_data, invoice_preview_lines
    fid = _patient("R23SEKInv")
    try:
        _seed_sek(fid)
        pat, rows, totals = invoice_data(fid)
        lines = "\n".join(invoice_preview_lines(pat, rows, totals, "detailed", "en", "Clinic"))
        assert "600.00 SEK" in lines and "1,000.00 SEK" in lines and "400.00 SEK" in lines
        assert "780,000" not in lines and "1,300,000" not in lines
        assert "SYP" not in lines  # single-currency doc: SEK only
        out = build_invoice_pdf(pat, rows, totals, "detailed", "en", "Clinic", TMP / "sek_invoice.pdf")
        txt = _pdf_text(out)
        if txt is not None:
            assert "SEK" in txt and "600.00" in txt and "1,000.00" in txt
            assert "780,000" not in txt and "SYP" not in txt
    finally: _cleanup(fid)
def test_sek_patient_report_is_raw_sek():
    from src.reports.pdf_report import create_patient_pdf
    from src.reports.report_text import patient_preview_lines
    fid = _patient("R23SEKRep")
    try:
        _seed_sek(fid)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT * FROM financials WHERE patient_file=?", (fid,)); rows = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT * FROM patients WHERE file_number=?", (fid,)); pat = dict(cur.fetchone()); conn.close()
        lines = "\n".join(patient_preview_lines(pat, [], [], [], rows, [], language="en"))
        assert "Total: 1000.00 SEK" in lines and "Paid: 600.00 SEK" in lines, lines
        assert "Remaining: 400.00 SEK" in lines
        assert "1300000" not in lines and "780000" not in lines
        out = create_patient_pdf(pat, [], [], [], rows, [], language="en", out_dir=TMP)
        txt = _pdf_text(out)
        if txt is not None:
            assert "SEK" in txt and "600.00" in txt
            assert "780,000" not in txt and "1,300,000" not in txt
    finally: _cleanup(fid)
def test_mixed_syp_sek_invoice_and_report_show_both():
    from src.reports.invoice_pdf import invoice_data, invoice_preview_lines
    from src.reports.report_text import patient_preview_lines
    fid = _patient("R23Mixed")
    try:
        save_financial(fid, "11", 500000, 300000, TODAY, currency="SYP", doctor=DOC, entered_by=DOC)
        _seed_sek(fid)
        pat, rows, totals = invoice_data(fid)
        lines = "\n".join(invoice_preview_lines(pat, rows, totals, "detailed", "en", "Clinic"))
        assert "300,000.00 SYP" in lines and "600.00 SEK" in lines  # own-currency payment lines
        assert "Total (SEK): 1,000.00 SEK" in lines and "Paid (SEK): 600.00 SEK" in lines
        assert "Remaining (SEK): 400.00 SEK" in lines
        assert "Total (SYP): 500,000.00 SYP" in lines and "Remaining (SYP): 200,000.00 SYP" in lines
        assert "501,000" not in lines  # the pre-fix folded sum
        rep = "\n".join(patient_preview_lines(pat, [], [], [], rows, [], language="en"))
        assert "Total (SEK): 1000.00 SEK" in rep and "Total (SYP): 500000.00 SYP" in rep
        assert "501000" not in rep and "501,000" not in rep
    finally: _cleanup(fid)
def test_no_rate_currency_raw_and_not_folded_into_base():
    """Foreign row with NO saved rate (direct insert, exchange_rate NULL):
    excluded from converted base totals, still RAW per currency."""
    fid = _patient("R23NoRate")
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("INSERT INTO financials(patient_file,tooth_number,total_cost,paid_amount,remaining,visit_date,currency,doctor,entered_by) VALUES(?,?,?,?,?,?,?,?,?)",
                    (fid, "11", 500, 500, 0, TODAY, "SEK", DOC, DOC)); conn.commit(); conn.close()
        assert patient_totals(fid) == {"total": 0.0, "paid": 0.0, "remaining": 0.0}
        assert totals_for_currency("SEK", TODAY, TODAY)["total_income"] >= 500.0  # raw, visible
        unc = [u for u in unconverted_totals(TODAY, TODAY) if u["currency"] == "SEK"]
        assert unc and unc[0]["paid"] >= 500.0, unc
        assert "SEK" in currencies_present()
        flex_before = flexible_totals(TODAY, TODAY)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("INSERT INTO financials(patient_file,tooth_number,total_cost,paid_amount,remaining,visit_date,currency,doctor,entered_by) VALUES(?,?,?,?,?,?,?,?,?)",
                    (fid, "12", 700, 700, 0, TODAY, "SEK", DOC, DOC)); conn.commit(); conn.close()
        flex_after = flexible_totals(TODAY, TODAY)
        assert flex_after["total_income"] == flex_before["total_income"]
        assert flex_after["total_debts"] == flex_before["total_debts"]
    finally: _cleanup(fid)
def test_finance_tab_gui_selector_shows_sek_raw():
    import tkinter as tk
    try: root = tk.Tk()
    except tk.TclError:
        print("SKIP finance tab GUI (no display)"); return
    root.withdraw()
    fid = _patient("R23SEKGui")
    try:
        _seed_sek(fid)
        from src.utils.finance_gate import FinanceGate
        class _StubApp:
            current_user = "fady"; current_role = "admin"
            current_patient = None; finance_gate = None; lang = "en"
        app = _StubApp(); app.finance_gate = FinanceGate(verify_fn=lambda u, p: True)
        from src.ui.finance import FinanceTab
        tab = FinanceTab(tk.Frame(root), app); root.update_idletasks()
        tab.e_gate_user.delete(0, tk.END); tab.e_gate_user.insert(0, "fady")
        tab.e_gate_pass.delete(0, tk.END); tab.e_gate_pass.insert(0, "x"); tab._try_unlock()
        tab.e_from.delete(0, "end"); tab.e_from.insert(0, TODAY)
        tab.e_to.delete(0, "end"); tab.e_to.insert(0, TODAY)
        from src.ui.finance_currency import on_currency_change, refresh_currency_selector
        refresh_currency_selector(tab)
        assert "SEK" in list(tab.cb_fin_cur.widget["values"]), tab.cb_fin_cur.widget["values"]
        exp = totals_for_currency("SEK", TODAY, TODAY)
        tab.cur_var.set("SEK"); on_currency_change(tab); root.update_idletasks()
        assert tab.cards["Total Income"].cget("text") == f"{exp['total_income']:.2f}"
        assert tab.cards["Total Debts"].cget("text") == f"{exp['total_debts']:.2f}"
        assert "SEK" in tab.lbl_usd.cget("text")
    finally: _cleanup(fid); root.destroy()
