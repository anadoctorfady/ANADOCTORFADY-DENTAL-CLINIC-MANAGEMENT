"""Patient info visibility regression (round 18 -> 21 -> 22).

Round 18 found the info panel pack-starved to height 1 in the
shell's fixed left column (invisible, Edit/Delete buttons with
it); round 21 made the whole column one scrollable canvas and
this test scrolled the panel into view before asserting.

Round 22 (owner redesign) supersedes the location again: the
panel is now the clinical tab's PINNED HEADER -- packed outside
the scroll canvas, so it is ALWAYS fully visible at the top of
the Clinical tab, no scrolling anywhere. The regression this
file now pins: the header is mapped at (nearly) its full height
at 1380x1000 and 1380x820, with a patient selected and with none
(placeholder state, buttons disabled but visible), and its
Edit/Delete buttons are inside the window WITHOUT any scroll.

Runs only against an isolated gate copy (ANADOCTORFADY_DATA_DIR
must be set); skips gracefully with no display. The gate copy's
fady password is reset to 1234 (throwaway copy only).
"""
import os
import time
import tkinter as tk
from unittest import mock


def _display_available():
    try:
        r = tk.Tk(); r.destroy(); return True
    except Exception:
        return False


def _find_login(app):
    for w in app.winfo_children():
        if isinstance(w, tk.Toplevel) and hasattr(w, "e_user"):
            return w
    return None


def _wait_login(app, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.update()
        win = _find_login(app)
        if win is not None:
            return win
        time.sleep(0.05)
    raise AssertionError("login window did not appear")


def _login(app):
    import src.ui.login as login_mod
    login = _wait_login(app)
    with mock.patch.object(login_mod.messagebox, "showinfo"):
        login.e_user.delete(0, tk.END); login.e_user.insert(0, "fady")
        login.e_pass.delete(0, tk.END); login.e_pass.insert(0, "1234")
        login.do_login()
    app.update()


def _select_any_patient(app):
    for q in ("a", "e", ""):
        app.search_var.set(q); app.update()
        kids = app.tree.get_children()
        if kids:
            app.tree.selection_set(kids[0]); app.on_select(); app.update()
            return True
    return False


def _assert_header_visible(app, geo, selected, min_h=100):
    app.geometry(geo); app.update_idletasks(); app.update()
    ip = app.info_panel
    # Round 22: the info panel is the clinical tab's pinned header.
    assert ip is app.clinical.header_panel
    assert ip.master is app.clinical
    assert ip.winfo_ismapped() == 1, f"header unmapped at {geo}"
    assert ip.winfo_height() >= min_h, (geo, ip.winfo_height())
    # NO scrolling: the header and its buttons are already inside
    # the window (that is the whole point of pinning it).
    for btn in (ip.edit_btn, ip.delete_btn, ip.refer_btn):
        assert btn.winfo_ismapped() == 1, f"button unmapped at {geo}"
        assert btn.winfo_height() >= 20, (geo, btn.winfo_height())
        top = btn.winfo_rooty(); bottom = top + btn.winfo_height()
        assert app.winfo_rooty() <= top, (geo, "button above window")
        assert bottom <= app.winfo_rooty() + app.winfo_height(), \
            (geo, "button below window bottom")
    if selected:
        assert str(ip.edit_btn["state"]) == "normal"
        assert str(ip.delete_btn["state"]) == "normal"  # fady = admin


def test_info_panel_mapped_at_real_window_sizes():
    if not os.environ.get("ANADOCTORFADY_DATA_DIR"):
        print("SKIP (not an isolated gate copy)"); return
    if not _display_available():
        print("SKIP (no display)"); return
    from src.models.database import get_connection
    from src.ui.shell import App
    from src.utils.auth import hash_pw
    conn = get_connection()
    conn.execute("UPDATE users SET password_hash=? WHERE username='fady'",
                 (hash_pw("1234"),))
    conn.commit(); conn.close()
    app = App()
    try:
        _login(app)
        assert _select_any_patient(app), "no patient rows in gate copy"
        assert app.current_patient is not None
        _assert_header_visible(app, "1380x1000", selected=True)
        _assert_header_visible(app, "1380x820", selected=True)
        # No patient open: header still fully mapped (placeholder),
        # buttons disabled.
        app.current_patient = None
        app.info_panel.refresh(None)
        app.update()
        _assert_header_visible(app, "1380x1000", selected=False, min_h=55)
        assert str(app.info_panel.edit_btn["state"]) == "disabled"
        assert str(app.info_panel.delete_btn["state"]) == "disabled"
    finally:
        try:
            app.destroy()
        except Exception:
            pass
