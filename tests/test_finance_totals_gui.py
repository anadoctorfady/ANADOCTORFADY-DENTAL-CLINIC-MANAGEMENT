"""FinanceTab GUI tests for flexible totals (Round 12, Job 9a):
the real checkboxes on the FinanceTab + the admin-only record
buttons. Model tests live in tests/test_finance_totals.py.
Skipped with no display (headless CI); exercised under Xvfb."""
from tests.test_finance_totals import TODAY, _setup, _teardown


class _StubApp:
    current_user = "fady"
    current_role = "admin"
    current_patient = None
    finance_gate = None


def _build_tab():
    """Unlocked admin FinanceTab, or None with no display."""
    import tkinter as tk
    from src.utils.finance_gate import FinanceGate
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.withdraw()
    app = _StubApp()
    app.finance_gate = FinanceGate(verify_fn=lambda u, p: True)
    from src.ui.finance import FinanceTab
    tab = FinanceTab(tk.Frame(root), app)
    root.update_idletasks()
    tab.e_gate_user.delete(0, tk.END); tab.e_gate_user.insert(0, "fady")
    tab.e_gate_pass.delete(0, tk.END); tab.e_gate_pass.insert(0, "x")
    tab._try_unlock()
    assert tab.gate.is_unlocked, "stub gate should unlock"
    return tab, root


def test_gui_toggles_change_cards():
    """Flipping the Lab checkbox clears the Lab card to '—' and
    raises Net by the lab amount; unchecking everything leaves
    Net == Income; the Included line names the components."""
    fid, exp_id, lab_id, sal_id = _setup()
    tab, root = _build_tab()
    if tab is None:
        print("SKIP test_gui_toggles_change_cards (no display)")
        _teardown(fid, exp_id, lab_id, sal_id)
        return
    try:
        tab.e_from.delete(0, "end"); tab.e_from.insert(0, TODAY)
        tab.e_to.delete(0, "end"); tab.e_to.insert(0, TODAY)
        tab.load(); tab.calc()
        root.update_idletasks()
        net_all = float(tab.cards["Net Income"].cget("text"))
        lab_txt = tab.cards["Total Lab"].cget("text")
        assert lab_txt != "—" and float(lab_txt) >= 10000.0
        assert "Lab" in tab.lbl_tot_included.cget("text") or "lab" in tab.lbl_tot_included.cget("text").lower()
        tab.tot_lab_var.set(False); tab.calc(); root.update_idletasks()
        assert tab.cards["Total Lab"].cget("text") == "—"
        assert float(tab.cards["Net Income"].cget("text")) == net_all + float(lab_txt)
        tab.tot_sal_var.set(False); tab.tot_exp_var.set(False); tab.calc()
        root.update_idletasks()
        assert tab.cards["Total Expenses"].cget("text") == "—"
        assert tab.cards["Net Income"].cget("text") == tab.cards["Total Income"].cget("text")
    finally:
        try: root.destroy()
        except Exception: pass
        _teardown(fid, exp_id, lab_id, sal_id)


def test_gui_record_buttons_admin_only():
    """No selection -> Edit/Delete disabled. Fresh expense row as
    admin -> enabled. Same row as doctor -> disabled + admin-only note."""
    fid, exp_id, lab_id, sal_id = _setup()
    tab, root = _build_tab()
    if tab is None:
        print("SKIP test_gui_record_buttons_admin_only (no display)")
        _teardown(fid, exp_id, lab_id, sal_id)
        return
    try:
        tab.e_from.delete(0, "end"); tab.e_from.insert(0, TODAY)
        tab.e_to.delete(0, "end"); tab.e_to.insert(0, TODAY)
        tab.load(); tab.calc(); root.update_idletasks()
        from src.ui.finance_records import refresh_record_buttons
        assert str(tab.btn_expense_edit.cget("state")) == "disabled"
        assert str(tab.btn_expense_del.cget("state")) == "disabled"
        tab.tree_exp.selection_set(str(exp_id))
        refresh_record_buttons(tab, tab.tree_exp, "expense")
        assert str(tab.btn_expense_edit.cget("state")) == "normal"
        assert str(tab.btn_expense_del.cget("state")) == "normal"
        tab._gate_role = "doctor"; tab._gate_user = "doc_x"
        refresh_record_buttons(tab, tab.tree_exp, "expense")
        assert str(tab.btn_expense_edit.cget("state")) == "disabled"
        assert "admin" in tab.lbl_expense_status.cget("text").lower()
    finally:
        try: root.destroy()
        except Exception: pass
        _teardown(fid, exp_id, lab_id, sal_id)
