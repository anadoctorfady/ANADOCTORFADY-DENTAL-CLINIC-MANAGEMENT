"""Items 10+11+12: no stats/telemetry UI in Settings, linking guide
opens with all key sections, Settings scrolls to Change Password,
Attendance Refresh button not clipped. GUI tests skip gracefully with
no display (same pattern as test_screenshot_fixes)."""
import contextlib
import tempfile
from pathlib import Path

import src.models.backup_validate as BV
import src.models.database as DBmod
from src.models.database import init_db
from src.ui.rounded_frame import RoundedFrame

ROOT = Path(__file__).resolve().parent.parent
_TMP = Path(tempfile.mkdtemp(prefix="settings_bundle_"))


@contextlib.contextmanager
def isolated_db():
    """Temp DB for GUI tests: other agents share the live clinic.db
    concurrently, so Settings/Attendance must not depend on its content."""
    db_path = _TMP / "iso_clinic.db"
    for suf in ("", "-wal", "-shm"):
        q = Path(str(db_path) + suf)
        if q.exists():
            q.unlink()
    old_db, old_bv = DBmod.DB, BV.DB
    DBmod.DB, BV.DB = db_path, db_path
    try:
        init_db()
        yield
    finally:
        DBmod.DB, BV.DB = old_db, old_bv


def _tk():
    try:
        import tkinter as tk
        return tk.Tk()
    except Exception:
        return None


class _StubApp:
    lang = "en"

    def print_pdf(self, bilingual=False):
        return None

    def _rebuild(self):
        return None


def test_no_telemetry_ui_in_settings():
    src = (ROOT / "src" / "ui" / "settings_ui.py").read_text(encoding="utf-8")
    low = src.lower()
    assert "telemetry" not in low, "Settings UI still mentions telemetry"
    assert "save telemetry url" not in low
    assert "tel_url_var" not in src and "INFO_TEXT" not in src
    # the silent sender itself must still work from the stored URL
    from src.models import telemetry as T
    assert callable(T.maybe_send_async) and callable(T.get_url)


def test_guide_opens_with_key_sections():
    from src.ui.settings_sync_guide import GUIDE_TEXT, open_linking_guide
    for key in ("sync server", "port 8001", "first-hosting safety",
                "Sync Now", "attendance", "troubleshooting",
                "fady", "1234", "LAN", "Center ID"):
        assert key.lower() in GUIDE_TEXT.lower(), f"guide missing: {key}"
    root = _tk()
    if root is None:
        return  # no display: text assertions above already ran
    try:
        root.update()
        win = open_linking_guide(root)
        root.update()
        assert win.winfo_exists()
        import tkinter as tk

        def _find_text(w):
            if isinstance(w, tk.Text):
                return w
            for ch in w.winfo_children():
                found = _find_text(ch)
                if found is not None:
                    return found
            return None

        # ScrolledText is a Frame wrapping a Text widget, not a Text itself
        text_w = _find_text(win)
        assert text_w is not None, "guide has no scrollable text widget"
        body = text_w.get("1.0", "end")
        assert "8001" in body and "Sync Now" in body and "fady" in body
        win.destroy()
    finally:
        root.destroy()


def test_settings_scrollable_change_password_reachable():
    from src.ui.settings_ui import SettingsTab
    root = _tk()
    if root is None:
        return  # no display: skip GUI check
    with isolated_db():
        _settings_scrollable_inner(root, SettingsTab)


def _settings_scrollable_inner(root, SettingsTab):
    try:
        root.geometry("900x500")
        tab = SettingsTab(root, _StubApp())
        tab.pack(fill="both", expand=True)
        root.update()
        assert hasattr(tab, "_canvas") and hasattr(tab, "body")
        # content is taller than a short viewport: scrolling is needed
        assert tab.body.winfo_reqheight() > tab._canvas.winfo_height()
        assert hasattr(tab, "pw_old") and hasattr(tab, "pw_new")
        # scroll to the very bottom: Change Password button must be
        # inside the visible viewport (not below the window edge)
        tab._canvas.yview_moveto(1.0)
        root.update()
        import tkinter as tk
        btns = [w for w in tab.body.winfo_children() if isinstance(w, RoundedFrame)
                and any(isinstance(c, tk.Label)
                        and "Change Password" in str(c.cget("text") or "")
                        for c in w.winfo_children())]
        assert btns, "Change Password section missing"
        frame = btns[0]
        top = frame.winfo_rooty()
        bottom = top + frame.winfo_height()
        view_top = tab._canvas.winfo_rooty()
        view_bottom = view_top + tab._canvas.winfo_height()
        assert top >= view_top and bottom <= view_bottom, \
            "Change Password section not visible after scrolling to bottom"
    finally:
        root.destroy()


def test_attendance_refresh_not_clipped():
    from src.ui.attendance_view import open_attendance_view
    root = _tk()
    if root is None:
        return  # no display: skip GUI check
    with isolated_db():
        _attendance_inner(root, open_attendance_view)


def _attendance_inner(root, open_attendance_view):
    try:
        root.update()
        win = open_attendance_view(root, "admin")
        assert win is not None
        root.update()
        import tkinter as tk
        flat = []
        for w in win.winfo_children():
            flat += list(w.winfo_children())
        btns = [w for w in flat if isinstance(w, tk.Button)
                and "Refresh" in str(w.cget("text") or "")]
        assert btns, "Refresh button missing"
        b = btns[0]
        assert b.winfo_ismapped(), "Refresh button not visible"
        assert b.winfo_x() + b.winfo_width() <= win.winfo_width(), \
            "Refresh button clipped at the right edge"
        win.destroy()
    finally:
        root.destroy()
