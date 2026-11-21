"""Round 21 (item 8): finance currencies are NOT limited to
SYP/USD.

(a) Entry points audited: the clinical payment currency picker
already offers the full searchable 178-currency list (asserted
here on the real widget); expenses/lab carry no currency by
design (base currency only, round 19). The one place that WAS
hardcoded was the Finance tab's "Today's rate" row -- USD only.
It now has a searchable picker over the full list, and the
manual rate box saves/loads a rate for ANY chosen pair.

(b) The per-currency selector is data-driven: seeding a payment
in EUR makes EUR appear in currencies_present(), in the Finance
tab selector, and in totals_for_currency() with exact RAW
totals. Runs against the isolated gate copy with setup/teardown
(the test_r19_currency_view pattern)."""
import tkinter as tk
from datetime import date
from unittest import mock

from src.models.database import get_connection, init_db, save_financial
from src.models.finance_currency import currencies_present, totals_for_currency
from src.models.currency import latest_rate
from src.utils.currencies import display_for_code

TODAY = date.today().isoformat()
DOC = "r21doc"


def _setup():
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name) VALUES(?,?)",
                ("R21Cur", "R21Cur Currency"))
    fid = cur.lastrowid
    conn.commit(); conn.close()
    save_financial(fid, "11", 300, 120, TODAY, currency="EUR", rate=11000,
                   rate_date=TODAY, doctor=DOC, entered_by=DOC)
    return fid


def _teardown(fid):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM financials WHERE patient_file=?", (fid,))
    cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    cur.execute("DELETE FROM exchange_rates WHERE from_currency='EUR'")
    conn.commit(); conn.close()


def test_eur_is_data_driven():
    before = totals_for_currency("EUR", TODAY, TODAY)
    assert "EUR" not in currencies_present() or before["total"] >= 0
    fid = _setup()
    try:
        assert "EUR" in currencies_present()
        eur = totals_for_currency("EUR", TODAY, TODAY)
        assert eur["total"] - before["total"] == 300.0
        assert eur["total_income"] - before["total_income"] == 120.0
        assert eur["total_debts"] - before["total_debts"] == 180.0
        assert eur["currency"] == "EUR"
    finally:
        _teardown(fid)


class _StubApp:
    current_user = "fady"; current_role = "admin"
    current_patient = None; finance_gate = None
    lang = "en"


def _finance_tab(root):
    from src.utils.finance_gate import FinanceGate
    app = _StubApp()
    app.finance_gate = FinanceGate(verify_fn=lambda u, p: True)
    from src.ui.finance import FinanceTab
    tab = FinanceTab(tk.Frame(root), app)
    root.update_idletasks()
    tab.e_gate_user.delete(0, tk.END); tab.e_gate_user.insert(0, "fady")
    tab.e_gate_pass.delete(0, tk.END); tab.e_gate_pass.insert(0, "x")
    tab._try_unlock()
    return tab


def test_finance_tab_selector_and_rate_row():
    try:
        root = tk.Tk()
    except tk.TclError:
        print("SKIP finance tab GUI (no display)"); return
    root.withdraw()
    fid = _setup()
    try:
        tab = _finance_tab(root)
        # (b) the per-currency selector lists EUR once it exists.
        from src.ui.finance_currency import refresh_currency_selector
        refresh_currency_selector(tab)
        assert "EUR" in list(tab.cb_fin_cur.widget["values"]), \
            tab.cb_fin_cur.widget["values"]
        # (a) the rate picker offers the FULL list, not just USD.
        vals = list(tab.cb_rate_from["values"])
        assert len(vals) >= 170, len(vals)
        eur_disp = display_for_code("EUR", "en")
        assert eur_disp in vals
        tab.rate_from_var.set(eur_disp)
        assert tab.rate_from_code() == "EUR"
        # The manual rate box saves a rate for the EUR pair.
        tab.e_rate_today.delete(0, tk.END); tab.e_rate_today.insert(0, "0.9")
        with mock.patch("src.ui.finance.messagebox.showinfo"), \
                mock.patch("src.ui.finance.messagebox.showerror"):
            tab.save_rate_today()
        assert latest_rate("EUR", tab.base_cur) == 0.9
    finally:
        _teardown(fid)
        root.destroy()


def test_clinical_payment_currency_full_list():
    try:
        root = tk.Tk()
    except tk.TclError:
        print("SKIP clinical currency GUI (no display)"); return
    root.withdraw()
    try:
        from src.ui.clinical import ClinicalTab
        from tests.test_clinical_save_gate import _stub_app
        tab = ClinicalTab(root, _stub_app())
        vals = list(tab.cb_cur["values"])
        assert len(vals) >= 170, len(vals)
        assert any(v.startswith("EUR") for v in vals), vals[:5]
        assert any(v.startswith("SYP") for v in vals)
        assert any(v.startswith("USD") for v in vals)
    finally:
        root.destroy()
