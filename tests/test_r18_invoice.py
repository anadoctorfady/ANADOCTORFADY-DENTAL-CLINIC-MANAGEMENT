"""Round 18 (item 8): patient invoice — detailed / summary.
Seeds a patient + financials DELTA rows on the gate DB copy and checks:
payment-row mapping (only rows with a paid component; amount = paid_syp;
date+time from visit_date + updated_at; tooth = what-for, empty tooth
falls back), detailed PDF contains every payment + the exact
patient_totals() numbers, summary PDF contains totals but NO per-payment
rows, a zero-payment invoice renders with remaining == total, an Arabic
invoice builds (reshaped labels extract via pdftotext), and the clinical
Print invoice button is disabled with no patient / enabled with one
(GUI, may flake under parallel load — coordinator re-runs sequentially).
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="r18_invoice_"))
_AR = re.compile(r"[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]")
FID, FID0 = 987001, 987002
# (visit_date, updated_at, tooth, total, paid) — row 3 is a charge
# only (paid 0): it counts in totals but is NOT a payment row.
ROWS = [("2026-11-01", "2026-11-01 09:30:00", "16", 400000, 250000),
        ("2026-11-05", "2026-11-05 14:05:00", "", 0, 120000),
        ("2026-11-06", "2026-11-06 10:00:00", "26", 200000, 0)]
TOTALS = {"total": 600000.0, "paid": 370000.0, "remaining": 230000.0}


def _pdf_text(path):
    if not shutil.which("pdftotext"):
        print("SKIP pdf-text check (no pdftotext)")
        return None
    r = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return r.stdout


def _seed(fid=FID, name="Invoice Test Patient", rows=ROWS):
    from src.models.database import get_connection, init_db
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM financials WHERE patient_file=?", (fid,))
    cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    cur.execute("INSERT INTO patients(file_number, full_name, birth_date_greg,"
                " nationality) VALUES(?,?,?,?)", (fid, name, "1990-01-01", "Syrian"))
    for vd, upd, tooth, tot, paid in rows:
        cur.execute("INSERT INTO financials(patient_file, tooth_number, total_cost,"
                    " paid_amount, remaining, visit_date, currency, total_syp,"
                    " paid_syp, remaining_syp, doctor, entered_by, updated_at)"
                    " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (fid, tooth, tot, paid, tot - paid, vd, "SYP", tot, paid,
                     tot - paid, "fady", "nurse1", upd))
    conn.commit(); conn.close()
    return fid


def _data(fid=FID):
    from src.reports.invoice_pdf import invoice_data
    return invoice_data(fid)


def test_invoice_totals_come_from_patient_totals():
    _seed()
    from src.models.finance import patient_totals
    assert patient_totals(FID) == TOTALS, patient_totals(FID)
    _pat, _rows, totals = _data()
    assert totals == TOTALS


def test_invoice_payment_rows_mapping():
    _seed()
    from src.reports.invoice_pdf import payment_rows, invoice_preview_lines
    _pat, rows, totals = _data()
    pr = payment_rows(rows)
    assert len(pr) == 2, pr  # the paid==0 charge row is not a payment
    assert pr[0] == {"when": "2026-11-01 09:30", "amount": 250000.0, "tooth": "16"}
    assert pr[1] == {"when": "2026-11-05 14:05", "amount": 120000.0, "tooth": ""}
    lines = "\n".join(invoice_preview_lines(_pat, rows, totals, "detailed", "en", "Smile Clinic", "SYP"))
    assert "Tooth 16" in lines and "General payment" in lines  # empty-tooth fallback
    assert "250,000.00" in lines and "120,000.00" in lines
    assert "600,000.00" in lines and "370,000.00" in lines and "230,000.00" in lines
    summ = "\n".join(invoice_preview_lines(_pat, rows, totals, "summary", "en", "Smile Clinic", "SYP"))
    assert "250,000.00" not in summ and "120,000.00" not in summ and "2026-11-01" not in summ
    assert "600,000.00" in summ and "230,000.00" in summ


def test_invoice_detailed_pdf():
    _seed()
    from src.reports.invoice_pdf import build_invoice_pdf
    pat, rows, totals = _data()
    out = build_invoice_pdf(pat, rows, totals, "detailed", "en", "Smile Clinic",
                            TMP / "detailed.pdf", currency="SYP")
    assert Path(out).exists() and Path(out).stat().st_size > 2000
    txt = _pdf_text(out)
    if txt is None:
        return
    assert "Smile Clinic" in txt and "ANADOCTORFADY" in txt
    for needle in ("250,000.00", "120,000.00", "2026-11-01", "09:30",
                   "2026-11-05", "14:05", "Tooth 16", "General payment",
                   "600,000.00", "370,000.00", "230,000.00"):
        assert needle in txt, needle
    assert "2026-11-06" not in txt  # charge-only row is not a payment
    assert not _AR.search(txt), "EN invoice must contain no Arabic chars"


def test_invoice_summary_pdf():
    _seed()
    from src.reports.invoice_pdf import build_invoice_pdf
    pat, rows, totals = _data()
    out = build_invoice_pdf(pat, rows, totals, "summary", "en", "Smile Clinic",
                            TMP / "summary.pdf", currency="SYP")
    assert Path(out).exists() and Path(out).stat().st_size > 2000
    txt = _pdf_text(out)
    if txt is None:
        return
    assert "Summary" in txt
    for needle in ("600,000.00", "370,000.00", "230,000.00"):
        assert needle in txt, needle
    for absent in ("250,000.00", "120,000.00", "2026-11-01", "09:30", "Payments"):
        assert absent not in txt, absent


def test_invoice_zero_payments():
    _seed(FID0, "Invoice Zero Patient", [("2026-11-02", "2026-11-02 08:00:00", "11", 150000, 0)])
    from src.reports.invoice_pdf import build_invoice_pdf, invoice_preview_lines
    pat, rows, totals = _data(FID0)
    assert totals == {"total": 150000.0, "paid": 0.0, "remaining": 150000.0}
    out = build_invoice_pdf(pat, rows, totals, "detailed", "en", "", TMP / "zero.pdf", currency="SYP")
    assert Path(out).exists()
    txt = _pdf_text(out)
    if txt is not None:
        assert "No payments recorded yet." in txt and "150,000.00" in txt
    lines = "\n".join(invoice_preview_lines(pat, rows, totals, "detailed", "en", "", "SYP"))
    assert "No payments recorded yet." in lines


def test_invoice_arabic_builds():
    _seed()
    from src.reports.invoice_pdf import build_invoice_pdf
    pat, rows, totals = _data()
    out = build_invoice_pdf(pat, rows, totals, "detailed", "ar", "Smile Clinic",
                            TMP / "detailed_ar.pdf", currency="SYP")
    assert Path(out).exists() and Path(out).stat().st_size > 5000
    txt = _pdf_text(out)
    if txt is None:
        return
    import arabic_reshaper
    for word in ("فاتورة", "الدفعات", "المجموع", "المدفوع", "المتبقي"):
        assert arabic_reshaper.reshape(word) in txt, word
    assert "250,000.00" in txt and "230,000.00 SYP" in txt  # remaining keeps its code
    assert "Invoice Test Patient" in txt  # Latin name survives in an AR invoice


def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)


def test_invoice_button_states_and_preview():
    import tkinter as tk
    try:
        probe = tk.Tk()
    except tk.TclError:
        print("SKIP invoice GUI test (no display)")
        return
    probe.destroy()
    _seed(FID, "Invoice Test Patient")
    import tkinter.messagebox as mb
    old_info, old_warn, old_err = mb.showinfo, mb.showwarning, mb.showerror
    mb.showinfo = mb.showwarning = mb.showerror = lambda *a, **k: None
    from src.ui.shell import App
    app = App()
    app._logged_in = True
    try:
        btn = app.clinical.btn_invoice
        assert "Print invoice" in str(btn.cget("text"))
        assert str(btn.cget("state")) == "disabled", "no patient -> disabled"
        app.load_patients(); app.select_patient(FID); app.update_idletasks()
        assert app.current_patient and app.current_patient["file_number"] == FID
        assert str(btn.cget("state")) == "normal", "patient open -> enabled"
        btn.invoke(); app.update_idletasks()
        wins = [w for w in _walk(app) if isinstance(w, tk.Toplevel) and "Invoice" in w.title()]
        assert wins, "Print invoice did not open the invoice preview"
        win = wins[0]
        body = next(w for w in _walk(win) if isinstance(w, tk.Text))
        assert "250,000.00" in body.get("1.0", tk.END)  # detailed by default
        radio = next(w for w in _walk(win) if isinstance(w, tk.Radiobutton) and str(w.cget("value")) == "summary")
        radio.invoke(); app.update_idletasks()  # click Summary (fires the kind command)
        assert "250,000.00" not in body.get("1.0", tk.END)  # summary hides payments
        assert "230,000.00" in body.get("1.0", tk.END)
        win.destroy(); app.update_idletasks()
        app.current_patient = None; app.clinical.clear(); app.update_idletasks()
        assert str(btn.cget("state")) == "disabled", "patient cleared -> disabled"
    finally:
        mb.showinfo, mb.showwarning, mb.showerror = old_info, old_warn, old_err
        try: app.destroy()
        except Exception: pass
