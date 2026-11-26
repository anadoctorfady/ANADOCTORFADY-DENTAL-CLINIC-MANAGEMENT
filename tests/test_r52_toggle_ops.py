"""Round 52, Section A: a language/theme toggle must not do the
wasted work the round-51 build did (profiled at 200k patients:
198 SQL, 519 PIL renders and all five lazy tabs built inside ONE
EN->AR toggle). Pinned here at seed scale:
- no lazy tab is built by startup, patient selection, or a toggle
  (tabs build on first open / attribute access only);
- a toggle executes only the SQL that repopulates the destroyed
  widgets with current data (< 60 statements; was 198);
- the SECOND build of a (language, theme) combination renders
  ZERO new PIL images (the tiered photo cache holds the set);
- set_setting() no longer invalidates the init_db memo (its write
  is schema-neutral), while the R31 external-write guard stands.
"""
import sys
from unittest import mock

from tests.test_r21_toggle_perf import _seed_200
from tests.test_templates_edit import isolated_db

_LAZY5 = ["about", "appt", "fin", "settings", "users"]


class _Counters:
    """Rebind get_connection / rounded_pil / gradient_pil in every
    loaded src.* module to counting wrappers (the gate runs all
    tests in one process, so import order must not matter)."""

    def __init__(self):
        self.sql = 0
        self.pil = 0
        self._saved = []

    def __enter__(self):
        import src.models.database as dbmod
        orig_gc = dbmod.get_connection

        def traced_gc(*a, **k):
            conn = orig_gc(*a, **k)

            def cb(_sql):
                self.sql += 1
            try:
                conn.set_trace_callback(cb)
            except Exception:
                pass
            return conn

        self._rebind("get_connection", orig_gc, traced_gc)
        import src.ui.rounded_render as rr
        for fn_name in ("rounded_pil", "gradient_pil"):
            orig = getattr(rr, fn_name)

            def make_counter(orig):
                def counted(*a, **k):
                    self.pil += 1
                    return orig(*a, **k)
                return counted
            self._rebind(fn_name, orig, make_counter(orig))
        return self

    def _rebind(self, name, orig, new):
        for mod in list(sys.modules.values()):
            if mod is None or not getattr(mod, "__name__", "").startswith("src."):
                continue
            if getattr(mod, name, None) is orig:
                self._saved.append((mod, name, orig))
                setattr(mod, name, new)

    def __exit__(self, *exc):
        for mod, name, orig in self._saved:
            setattr(mod, name, orig)
        self._saved = []
        return False

    def reset(self):
        self.sql = 0
        self.pil = 0


def test_toggle_builds_no_lazy_tabs_and_little_sql():
    from tkinter import messagebox
    from src.ui.shell import App
    from tests.test_r18_info_panel_visible import _login
    with isolated_db():
        _seed_200()
        messagebox.showinfo = lambda *a, **k: None
        app = App()
        try:
            _login(app)
            app.deiconify(); app.geometry("1380x1000"); app.update()
            assert sorted(app._lazy_tabs) == _LAZY5, sorted(app._lazy_tabs)
            app.search_var.set("Pat"); app.load_patients(); app.update()
            kids = app.tree.get_children("")
            assert kids, "seed patients missing"
            app.tree.selection_set(kids[0]); app.on_select(); app.update()
            # Patient selection must not build Appointments either.
            assert sorted(app._lazy_tabs) == _LAZY5, sorted(app._lazy_tabs)
            with _Counters() as c:
                app._toggle_lang(); app.update()
                assert c.sql < 60, f"EN->AR toggle ran {c.sql} SQL"
                assert sorted(app._lazy_tabs) == _LAZY5
                c.reset()
                app._toggle_lang(); app.update()  # AR->EN
                assert c.sql < 60, f"AR->EN toggle ran {c.sql} SQL"
                c.reset()
                app._toggle_theme(); app.update()
                assert c.sql < 60, f"theme toggle ran {c.sql} SQL"
                assert sorted(app._lazy_tabs) == _LAZY5
                app._toggle_theme(); app.update()  # back to light: the (AR, light) combo is warm now
                c.reset()
                app._toggle_lang(); app.update()  # EN->AR, warm combo
                assert c.pil == 0, f"warm EN->AR rendered {c.pil} images"
                assert c.sql < 60, f"warm EN->AR ran {c.sql} SQL"
        finally:
            app.destroy()


def test_set_setting_keeps_init_memo_armed():
    import hashlib
    from pathlib import Path
    import src.models.database as DBmod
    from src.models.database import init_db, set_setting

    def snap():
        s = DBmod.DB.stat()
        return (s.st_mtime_ns, s.st_size,
                hashlib.md5(Path(DBmod.DB).read_bytes()).hexdigest())

    with isolated_db():
        init_db()
        set_setting("language", "ar")  # the toggle's own write
        before = snap()
        init_db()  # must be a no-op: the schema did not change
        assert snap() == before, "set_setting invalidated the init memo"
        set_setting("language", "en")
        before = snap()
        init_db()
        assert snap() == before, "set_setting invalidated the init memo"
