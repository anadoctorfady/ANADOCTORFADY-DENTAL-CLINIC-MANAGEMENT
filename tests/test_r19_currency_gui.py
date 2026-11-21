"""Round 19 (R19-E) GUI tests for the per-currency finance view:
the real FinanceTab selector switching the cards All <-> one
currency (raw), and the clinical per-currency breakdown block.
Model tests + seed helpers live in tests.test_r19_currency_view.
Skipped with no display; exercised under Xvfb (DISPLAY=:98)."""
from src.models.database import get_connection, save_financial
from src.models.finance_totals import flexible_totals
from tests.test_r19_currency_view import TODAY, DOC, _setup, _teardown


def test_gui_selector_switches_cards():
    """Real FinanceTab (admin): All shows converted totals; picking
    USD shows raw USD totals with the currency code noted."""
    import tkinter as tk
    from src.utils.finance_gate import FinanceGate

    class _StubApp:
        current_user = "fady"; current_role = "admin"
        current_patient = None; finance_gate = None
        lang = "en"

    fid, e, l = _setup()
    try:
        root = tk.Tk()
    except tk.TclError:
        _teardown(fid, e, l)
        print("SKIP test_gui_selector_switches_cards (no display)")
        return
    try:
        root.withdraw()
        app = _StubApp()
        app.finance_gate = FinanceGate(verify_fn=lambda u, p: True)
        from src.ui.finance import FinanceTab
        tab = FinanceTab(tk.Frame(root), app)
        root.update_idletasks()
        tab.e_gate_user.delete(0, tk.END); tab.e_gate_user.insert(0, "fady")
        tab.e_gate_pass.delete(0, tk.END); tab.e_gate_pass.insert(0, "x")
        tab._try_unlock()
        assert tab.gate.is_unlocked
        tab.e_from.delete(0, "end"); tab.e_from.insert(0, TODAY)
        tab.e_to.delete(0, "end"); tab.e_to.insert(0, TODAY)
        assert "USD" in tab.cb_fin_cur.widget["values"]
        tab.calc(); root.update_idletasks()
        exp_all = flexible_totals(TODAY, TODAY)
        assert tab.cards["Total Income"].cget("text") == \
            f"{exp_all['total_income']:.2f}"
        tab.cur_var.set("USD")
        from src.ui.finance_currency import on_currency_change
        on_currency_change(tab); root.update_idletasks()
        assert tab.cards["Total Income"].cget("text") == "50.00"
        assert tab.cards["Total Debts"].cget("text") == "150.00"
        assert tab.cards["Net Income"].cget("text") == "50.00"
        assert "USD" in tab.lbl_usd.cget("text")
        tab.cur_var.set(tab._cur_all_label); tab.calc()
        root.update_idletasks()
        assert tab.cards["Total Income"].cget("text") == \
            f"{exp_all['total_income']:.2f}"
    finally:
        try: root.destroy()
        except Exception: pass
        _teardown(fid, e, l)


def test_clinical_breakdown_block():
    """Breakdown label: >1 currency -> one raw line per currency;
    single-currency patient -> label stays unpacked (no block)."""
    import tkinter as tk
    from types import SimpleNamespace
    fid, e, l = _setup()
    single = None
    try:
        root = tk.Tk()
    except tk.TclError:
        _teardown(fid, e, l)
        print("SKIP test_clinical_breakdown_block (no display)")
        return
    try:
        root.withdraw()
        conn = get_connection(); cur = conn.cursor()
        cur.execute("INSERT INTO patients(first_name,full_name) VALUES(?,?)",
                    ("R19One", "R19One Single"))
        single = cur.lastrowid; conn.commit(); conn.close()
        save_financial(single, "11", 7000, 7000, TODAY, currency="SYP",
                       doctor=DOC, entered_by=DOC)
        from src.ui.clinical_currency import (build_currency_breakdown,
                                              refresh_currency_breakdown)
        frame = tk.Frame(root); frame.pack()
        tab = SimpleNamespace(app=SimpleNamespace(lang="en"))
        build_currency_breakdown(tab, frame)
        refresh_currency_breakdown(tab, fid); root.update_idletasks()
        txt = tab.lbl_cur_break.cget("text")
        assert tab.lbl_cur_break.winfo_manager() == "pack"
        assert "SYP" in txt and "USD" in txt and "150.00" in txt, txt
        refresh_currency_breakdown(tab, single); root.update_idletasks()
        assert tab.lbl_cur_break.winfo_manager() == ""
    finally:
        try: root.destroy()
        except Exception: pass
        if single is not None:
            conn = get_connection(); cur = conn.cursor()
            cur.execute("DELETE FROM financials WHERE patient_file=?", (single,))
            cur.execute("DELETE FROM patients WHERE file_number=?", (single,))
            conn.commit(); conn.close()
        _teardown(fid, e, l)
