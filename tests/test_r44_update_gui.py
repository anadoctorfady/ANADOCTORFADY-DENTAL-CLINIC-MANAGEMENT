"""Round 44 GUI tests: the update notice + dialog (the model
half is covered in test_r44_update). A stub app — a Tk root with
a top-bar frame and a lang attribute — drives the REAL update_ui
widgets: the notice appears only for a newer undismissed
release; Later dismisses + persists; Download is exercised with
a fake local "installer" (updater.download_installer faked,
os.startfile mocked — a real installer is never launched) and a
failed download leaves the app running. Skips without a
display. <200 lines."""
import os, tempfile, time
from pathlib import Path
from unittest.mock import patch
import tkinter as tk

from src.models import updater
from src.models.database import get_setting
from src.config.strings_r44 import r44_t
from src.ui import update_ui
from tests.test_templates_edit import isolated_db
from tests.test_r44_update import INFO

_STATUS_KEYS = ("update.downloading", "update.installing",
                "update.failed", "update.invalid")


def _root():
    try:
        return tk.Tk()
    except tk.TclError:
        return None


def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)


def _stub_app(root, lang="en"):
    root.lang = lang
    bar = tk.Frame(root, bg="#7C3AED", height=48)
    bar.pack(fill="x")
    root._topbar_frame = bar
    return root


def _btn(win, text):
    return next(w for w in _walk(win)
                if isinstance(w, tk.Button) and w.cget("text") == text)


def _status(win, lang="en"):
    texts = {r44_t(k, lang) for k in _STATUS_KEYS}
    for w in _walk(win):
        if isinstance(w, tk.Label) and w.cget("text") in texts:
            return w.cget("text")
    return ""


def _pump(root, cond, secs=4.0):
    end = time.time() + secs
    while time.time() < end:
        root.update()
        if cond():
            return True
        time.sleep(0.05)
    return cond()


def _cleanup(root):
    update_ui._PENDING["info"] = None
    try:
        root.destroy()
    except Exception:
        pass


def test_banner_appears_only_when_pending():
    root = _root()
    if root is None:
        return
    try:
        app = _stub_app(root)
        assert update_ui.attach(app) is None  # nothing pending
        assert getattr(app, "_update_btn", None) is None
        update_ui._PENDING["info"] = INFO
        btn = update_ui.attach(app)
        assert btn is not None and "9.9.9" in btn.cget("text")
        assert update_ui.attach(app) is btn  # never duplicated
        update_ui.detach(app)
        assert update_ui.pending() is None
        assert not btn.winfo_exists()
    finally:
        _cleanup(root)


def test_dialog_later_dismisses_and_persists():
    root = _root()
    if root is None:
        return
    try:
        with isolated_db():
            app = _stub_app(root)
            update_ui._PENDING["info"] = INFO
            btn = update_ui.attach(app)
            dlg = update_ui.open_update_dialog(app)
            root.update()
            _btn(dlg, r44_t("update.later", "en")).invoke()
            root.update()
            assert get_setting(updater.KEY_DISMISSED) == "v9.9.9"
            assert update_ui.pending() is None
            assert not btn.winfo_exists()
            assert not dlg.winfo_exists()
    finally:
        _cleanup(root)


def test_dialog_download_launches_and_exits():
    root = _root()
    if root is None:
        return
    calls = {"start": [], "destroy": 0}
    dest = str(Path(tempfile.mkdtemp()) / "ANADOCTORFADY_Setup.exe")
    real_destroy = root.destroy

    def fake_dl(url, dest_arg=None, progress=None):
        assert url == INFO["url"]
        if progress:
            progress(5, 5)
        return ("ok", dest)

    try:
        app = _stub_app(root)
        root.destroy = lambda: calls.__setitem__(
            "destroy", calls["destroy"] + 1)
        update_ui._PENDING["info"] = INFO
        dlg = update_ui.open_update_dialog(app)
        with patch.object(updater, "download_installer", fake_dl), \
                patch.object(os, "startfile",
                             lambda p: calls["start"].append(p),
                             create=True):
            _btn(dlg, r44_t("update.download", "en")).invoke()
            assert _pump(root, lambda: bool(calls["start"]))
        assert calls["start"] == [dest]  # the validated file only
        assert calls["destroy"] == 1     # app exits for the install
    finally:
        root.destroy = real_destroy
        _cleanup(root)


def test_dialog_download_failure_keeps_app_running():
    root = _root()
    if root is None:
        return
    started = []
    try:
        app = _stub_app(root)
        update_ui._PENDING["info"] = INFO
        dlg = update_ui.open_update_dialog(app)
        failed = r44_t("update.failed", "en")
        invalid = r44_t("update.invalid", "en")
        with patch.object(os, "startfile",
                          lambda p: started.append(p), create=True):
            with patch.object(
                    updater, "download_installer",
                    lambda url, dest=None, progress=None:
                        ("failed", None)):
                _btn(dlg, r44_t("update.download", "en")).invoke()
                assert _pump(root, lambda: _status(dlg) == failed)
            assert not started and dlg.winfo_exists()
            # retry after failure: an invalid file, its own message
            with patch.object(
                    updater, "download_installer",
                    lambda url, dest=None, progress=None:
                        ("invalid", None)):
                _btn(dlg, r44_t("update.download", "en")).invoke()
                assert _pump(root, lambda: _status(dlg) == invalid)
            assert not started and dlg.winfo_exists()
    finally:
        _cleanup(root)
