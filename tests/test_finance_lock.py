"""15-minute finance auto-lock (Round 12, Job 9b): is_unlocked() goes
False once TIMEOUT_SECONDS (900) pass without ANY finance activity;
any activity (touch / unlock / calc / toggle) resets the timer; when
the lock engages, ALL finance numbers are hidden/cleared and the
password prompt returns until re-auth. Tests monkeypatch
TIMEOUT_SECONDS to 1-2 seconds — there is NO test backdoor in the
production UI."""
import time
import src.utils.finance_gate as fg_mod
from src.utils.finance_gate import FinanceGate


def _gate():
    return FinanceGate(verify_fn=lambda u, p: (u, p) == ("fady", "1234"))


def test_timeout_constant_is_15_minutes():
    assert fg_mod.TIMEOUT_SECONDS == 900


def test_locked_by_default_and_wrong_password_stays_locked():
    g = _gate()
    assert g.is_unlocked is False
    assert g.try_unlock("fady", "wrong") is False
    assert g.is_unlocked is False


def test_unlock_then_timeout_locks():
    g = _gate()
    assert g.try_unlock("fady", "1234") is True
    assert g.is_unlocked is True
    fg_mod.TIMEOUT_SECONDS = 1
    try:
        time.sleep(1.2)
        assert g.is_unlocked is False
    finally:
        fg_mod.TIMEOUT_SECONDS = 900


def test_activity_resets_timer():
    """touch() inside the window keeps the gate open past the first
    deadline; silence after the last touch still locks it."""
    g = _gate()
    assert g.try_unlock("fady", "1234") is True
    fg_mod.TIMEOUT_SECONDS = 2
    try:
        time.sleep(1.2)
        g.touch()  # activity resets the 2s timer
        time.sleep(1.2)
        assert g.is_unlocked is True, "touch should have reset the timer"
        time.sleep(2.2)
        assert g.is_unlocked is False, "silence after the last touch locks"
    finally:
        fg_mod.TIMEOUT_SECONDS = 900


def test_touch_never_unlocks_and_lock_clears_timer():
    g = _gate()
    g.touch()  # locked gate: touch must not unlock
    assert g.is_unlocked is False
    assert g.try_unlock("fady", "1234") is True
    g.lock()
    assert g.is_unlocked is False
    g.touch()
    assert g.is_unlocked is False
    # Re-auth after a timeout unlocks again.
    fg_mod.TIMEOUT_SECONDS = 1
    try:
        assert g.try_unlock("fady", "1234") is True
        time.sleep(1.2)
        assert g.is_unlocked is False
        assert g.try_unlock("fady", "1234") is True
        assert g.is_unlocked is True
    finally:
        fg_mod.TIMEOUT_SECONDS = 900


class _StubApp:
    current_user = "fady"
    current_role = "admin"
    current_patient = None
    finance_gate = None


def _build_tab():
    """Unlocked admin FinanceTab, or (None, None) with no display."""
    import tkinter as tk
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
    tab.load(); tab.calc(); root.update_idletasks()
    return tab, root


def test_gui_lock_hides_all_numbers_and_prompt_returns():
    """After the (shortened) timeout the view shows no numbers — cards
    '—', USD line empty, trees empty — and the lock overlay is back;
    re-auth unlocks and the numbers return."""
    tab, root = _build_tab()
    if tab is None:
        print("SKIP test_gui_lock_hides_all_numbers_and_prompt_returns (no display)")
        return
    from src.ui.finance_records import check_auto_lock
    try:
        # place_info() (not winfo_ismapped, the root is withdrawn in
        # tests) tells whether the lock overlay is placed or forgotten.
        assert tab._lock.place_info() == {}, "unlocked: no prompt"
        assert tab.cards["Total Income"].cget("text") != "—"
        fg_mod.TIMEOUT_SECONDS = 1
        try:
            time.sleep(1.2)
            assert tab.gate.is_unlocked is False
            assert check_auto_lock(tab) is True
            root.update_idletasks()
            for lbl in tab.cards.values():
                assert lbl.cget("text") == "—", f"card still shows {lbl.cget('text')!r}"
            assert tab.lbl_usd.cget("text") == ""
            for tr in (tab.tree_exp, tab.tree_lab, tab.tree_debt, tab.tree_centers):
                assert not tr.get_children(), "tree still holds rows after lock"
            assert tab._lock.place_info() != {}, "password prompt should be back"
            assert "15" in tab.lbl_gate_auto.cget("text")
            # Re-auth unlocks again and the numbers return.
            tab.e_gate_pass.delete(0, "end"); tab.e_gate_pass.insert(0, "x")
            tab._try_unlock()
            assert tab.gate.is_unlocked is True
            assert tab._lock.place_info() == {}
            assert tab.cards["Total Income"].cget("text") != "—"
        finally:
            fg_mod.TIMEOUT_SECONDS = 900
    finally:
        try: root.destroy()
        except Exception: pass


def test_gui_activity_via_calc_resets_timer():
    """Calling calc() (finance activity) inside the window keeps the
    gate open; without further activity it locks."""
    tab, root = _build_tab()
    if tab is None:
        print("SKIP test_gui_activity_via_calc_resets_timer (no display)")
        return
    try:
        fg_mod.TIMEOUT_SECONDS = 2
        try:
            time.sleep(1.2)
            tab.calc()  # activity resets the timer
            time.sleep(1.2)
            assert tab.gate.is_unlocked is True
            time.sleep(2.2)
            assert tab.gate.is_unlocked is False
        finally:
            fg_mod.TIMEOUT_SECONDS = 900
    finally:
        try: root.destroy()
        except Exception: pass
