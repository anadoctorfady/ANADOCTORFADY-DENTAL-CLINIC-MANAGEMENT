"""Sync Now button (2026-11-07): password prompted every sync and
never stored, offline-safe, pushed/pulled counts. GUI test skips
with no display; handler tests use a fake tab + stubbed sync_fn."""
from src.models.database import get_connection, init_db
from src.models.sync import sync_now
from src.ui import sync_now_ui
from src.utils import auth
from src.utils.auth import set_current_user


class _FakeVar:
    def __init__(self, value): self._v = value
    def get(self): return self._v
    def set(self, value): self._v = value


class _FakeTab:
    """Duck-typed SettingsTab: only the two vars do_sync_now reads."""
    def __init__(self, url="http://127.0.0.1:9", center="main"):
        self.sync_url_var = _FakeVar(url)
        self.sync_center_var = _FakeVar(center)


def _as_user(username):
    """Log in `username`; returns saved session to restore after."""
    saved = dict(auth._CURRENT); set_current_user(username); return saved


def _restore(saved):
    auth._CURRENT.update(saved)


def _settings_tab():
    """Real SettingsTab under xvfb. Raises if there is no display."""
    import tkinter as tk
    from tkinter import ttk
    from src.ui.settings_ui import SettingsTab
    init_db()
    root = tk.Tk(); root.withdraw()
    nb = ttk.Notebook(root); nb.pack()
    tab = SettingsTab(nb, app=None)
    nb.add(tab, text="  Settings / Reports  ")
    return root, tab


def _sync_frame(tab):
    """'Multi-device sync' section, nested in the scrollable body.
    Round 13: a RoundedFrame titled by a heading Label (not a
    LabelFrame); return its .inner, where the button lives."""
    import tkinter as tk; from src.ui.rounded_frame import RoundedFrame
    for w in tab.winfo_children():
        if isinstance(w, RoundedFrame) and any(isinstance(c, tk.Label)
                and "Multi-device sync" in str(c.cget("text") or "")
                for c in w.winfo_children()):
            return w.inner
        if (found := _sync_frame(w)) is not None:
            return found
    return None


def test_sync_button_in_settings_sync_frame():
    """Sync frame holds a 'Sync Now' button (single-language, round 16);
    clicking it runs the sync handler (stubbed) and shows its result message."""
    try:
        root, tab = _settings_tab()
    except Exception:
        return  # no display: skip GUI check
    try:
        frame = _sync_frame(tab)
        assert frame is not None, "sync frame missing from SettingsTab"
        btns = [c for c in frame.winfo_children()
                if c.winfo_class() == "Button" and "Sync Now" in str(c.cget("text"))]
        assert len(btns) == 1, [str(c.cget("text")) for c in frame.winfo_children()]
        assert str(btns[0].cget("text")).strip() == "🔄 Sync Now"
        assert tab.sync_now_btn is btns[0]
        called, shown = [], []

        def _fake_do_sync(settings_tab):
            called.append(settings_tab)
            return "ok", "Sync done — pushed 0", {}

        real_do_sync, real_box = sync_now_ui.do_sync_now, sync_now_ui.messagebox
        import types
        sync_now_ui.do_sync_now = _fake_do_sync
        sync_now_ui.messagebox = types.SimpleNamespace(
            showinfo=lambda *a: shown.append(("info",) + a),
            showerror=lambda *a: shown.append(("error",) + a))
        try:
            btns[0].invoke()
        finally:
            sync_now_ui.do_sync_now = real_do_sync
            sync_now_ui.messagebox = real_box
        assert called == [tab], "button did not call the sync handler"
        assert shown and shown[0][0] == "info" and "Sync done" in shown[0][2], shown
    finally:
        try: root.destroy()
        except Exception: pass


def test_handler_passes_url_center_user_and_prompted_password():
    """Handler calls sync_now with the entered URL/center, the logged-in
    username, and the password from the prompt (stubbed, no real server)."""
    init_db()
    saved = _as_user("fady")
    try:
        seen = {}

        def fake_sync(conn, url, user, password, center):
            seen.update(url=url, user=user, password=password, center=center)
            return {"offline": False, "login": True, "push": 3,
                    "pull": {"patients": 1, "visits": 2, "financials": 0,
                             "employees": 0}, "errors": []}

        status, msg, res = sync_now_ui.do_sync_now(
            _FakeTab(), sync_fn=fake_sync,
            prompt_fn=lambda parent, user: "pw1234")
        assert status == "ok", (status, msg)
        assert seen == {"url": "http://127.0.0.1:9", "user": "fady",
                        "password": "pw1234", "center": "main"}, seen
        assert "pushed 3" in msg and "patients 1" in msg and "visits 2" in msg, msg
        assert "Sync done" in msg and "تمت المزامنة" not in msg, msg
    finally:
        _restore(saved)


def test_not_logged_in_shows_error_without_prompting():
    """No user logged in -> single-language error, password never prompted,
    sync never runs."""
    init_db()
    saved = _as_user(None)
    try:
        def _never(*a):
            raise AssertionError("must not prompt/sync when not logged in")

        status, msg, res = sync_now_ui.do_sync_now(
            _FakeTab(), sync_fn=_never, prompt_fn=_never)
        assert status == "not_logged_in", (status, msg)
        assert "Not logged in" in msg and "لم يتم تسجيل الدخول" not in msg, msg
    finally:
        _restore(saved)


def test_login_failed_message():
    """Wrong credentials -> login_failed with the single-language message."""
    init_db()
    saved = _as_user("fady")
    try:
        status, msg, res = sync_now_ui.do_sync_now(
            _FakeTab(),
            sync_fn=lambda *a: {"offline": False, "login": False,
                                "push": None, "pull": None,
                                "errors": ["invalid credentials"]},
            prompt_fn=lambda parent, user: "wrongpw")
        assert status == "login_failed", (status, msg)
        assert "Login failed" in msg and "فشل الدخول" not in msg, msg
    finally:
        _restore(saved)


def test_cancelled_prompt_does_not_sync():
    """Closing the password prompt cancels: no sync call, no error."""
    init_db()
    saved = _as_user("fady")
    try:
        def _never(*a):
            raise AssertionError("must not sync after cancel")

        status, msg, res = sync_now_ui.do_sync_now(
            _FakeTab(), sync_fn=_never, prompt_fn=lambda parent, user: None)
        assert status == "cancelled", (status, msg)
    finally:
        _restore(saved)


def test_offline_empty_url_returns_offline_without_raising():
    """Empty URL -> offline result, no password prompt, no sync call;
    and sync_now itself is offline-safe at the model level."""
    init_db()
    saved = _as_user("fady")
    try:
        def _never(*a):
            raise AssertionError("must not prompt/sync when offline")

        called = []
        status, msg, res = sync_now_ui.do_sync_now(
            _FakeTab(url=""), sync_fn=lambda *a: called.append(a),
            prompt_fn=_never)
        assert status == "offline", (status, msg)
        assert not called, "sync must not run with an empty URL"
        assert res.get("offline") is True
        assert "Offline" in msg and "بلا اتصال" not in msg, msg
        conn = get_connection()
        try:
            res = sync_now(conn, "", "fady", "pw", "main")
        finally:
            conn.close()
        assert res.get("offline") is True and res.get("login") is False
    finally:
        _restore(saved)

