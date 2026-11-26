"""Round 44 UI: the update notice in the top bar + its dialog.

maybe_check_async(app) is called once from the shell's silent
startup hook; it delegates the throttled check to models.updater
on a daemon thread and, only when a newer undismissed release
exists, attaches a slim button to the top bar (on the Tk main
thread, via after(0)). Clicking it opens the dialog:
"Download & install" — the ONLY path that ever downloads or
launches anything — or "Later", which dismisses that tag for
good (a still newer release may notify again). Every failure
is silent: no notice, no error, the app unaffected. <200 lines.
"""
import os
import threading
import tkinter as tk
from tkinter import ttk

from src.config.theme import current
from src.config.strings_r44 import r44_t
from src.models import updater
from src.ui.rounded import rounded_button

_PENDING = {"info": None}
_STARTED = {"done": False}


def pending():
    return _PENDING["info"]


def maybe_check_async(app):
    """Once per launch: start the silent background check."""
    if _STARTED["done"]:
        return
    _STARTED["done"] = True

    def _found(info):
        _PENDING["info"] = info
        try:
            app.after(0, lambda: attach(app))
        except Exception:
            pass

    try:
        updater.check_async(_found)
    except Exception:
        pass


def attach(app):
    """Show the slim top-bar notice when a release is pending.
    Called by the check callback and at every top-bar build, so a
    theme/language rebuild re-shows it in the new language.
    Returns the button (existing or new), else None."""
    info = _PENDING["info"]
    if not info:
        return None
    btn = getattr(app, "_update_btn", None)
    try:
        if btn is not None and btn.winfo_exists():
            return btn
    except Exception:
        pass
    bar = getattr(app, "_topbar_frame", None)
    if bar is None:
        return None
    th = current()
    lang = getattr(app, "lang", "en")
    btn = rounded_button(
        bar, text=f"{r44_t('update.available', lang)} {info['version']}",
        bg=th["header2"], fg="white",
        command=lambda: open_update_dialog(app))
    btn.pack(side="right", padx=8, pady=8)
    app._update_btn = btn
    return btn


def detach(app):
    """Remove the notice (the release was dismissed)."""
    _PENDING["info"] = None
    btn = getattr(app, "_update_btn", None)
    try:
        if btn is not None and btn.winfo_exists():
            btn.destroy()
    except Exception:
        pass
    app._update_btn = None


def _launch_and_exit(app, path):
    """Launch the validated installer, then close the app so the
    installer can replace its files. False when the launch itself
    failed (nothing was started; the app keeps running)."""
    try:
        os.startfile(path)  # Windows: opens the setup wizard
    except Exception:
        return False
    try:
        app.destroy()
    except Exception:
        pass
    return True


def open_update_dialog(app):
    """The update dialog for the pending release. Non-modal; the
    window's X just closes it (no dismissal — only Later does)."""
    info = _PENDING["info"]
    if not info:
        return None
    dlg = getattr(app, "_update_dialog", None)
    try:
        if dlg is not None and dlg.winfo_exists():
            dlg.lift()
            return dlg
    except Exception:
        pass
    lang = getattr(app, "lang", "en")
    th = current()
    win = tk.Toplevel(app)
    app._update_dialog = win
    win.title(r44_t("update.title", lang))
    win.configure(bg=th["bg"])
    win.resizable(False, False)
    body = tk.Frame(win, bg=th["bg"])
    body.pack(fill="both", expand=True, padx=16, pady=12)
    tk.Label(body, text=r44_t("update.body", lang).format(
        version=info["version"]), bg=th["bg"], fg=th["text"],
        wraplength=380, justify="left").pack(anchor="w")
    status = tk.Label(body, text="", bg=th["bg"], fg=th["text"])
    status.pack(anchor="w", pady=(8, 0))
    bar_w = ttk.Progressbar(body, mode="determinate", maximum=100,
                            length=380)
    state = {"busy": False, "result": None, "done": 0, "total": None}

    def _later():
        updater.dismiss(info["tag"])
        detach(app)
        win.destroy()

    btns = tk.Frame(body, bg=th["bg"])
    btns.pack(fill="x", pady=(12, 0))
    dl_btn = rounded_button(btns, text=r44_t("update.download", lang),
                            bg=th["header2"], fg="white")
    dl_btn.pack(side="left")
    rounded_button(btns, text=r44_t("update.later", lang),
                   bg=th["panel"], fg=th["text"],
                   command=_later).pack(side="right")

    def _progress(done, total):
        state["done"], state["total"] = done, total

    def _poll():
        try:
            if not win.winfo_exists():
                return
        except Exception:
            return
        if state["result"] is None:
            if state["total"]:
                bar_w.configure(
                    value=100.0 * state["done"] / state["total"])
            win.after(120, _poll)
            return
        kind, path = state["result"]
        if kind == "ok":
            status.configure(text=r44_t("update.installing", lang))
            win.update_idletasks()
            if _launch_and_exit(app, path):
                return
            kind = "failed"  # launch failed: fall through to error
        key = "update.invalid" if kind == "invalid" else "update.failed"
        status.configure(text=r44_t(key, lang), fg="#B91C1C")
        bar_w.pack_forget()
        state["busy"] = False
        dl_btn.configure(state="normal")

    def _download():
        if state["busy"]:
            return
        state["busy"] = True
        dl_btn.configure(state="disabled")
        status.configure(text=r44_t("update.downloading", lang),
                         fg=th["text"])
        bar_w.configure(value=0)
        bar_w.pack(anchor="w", pady=(4, 0))

        def _work():
            state["result"] = updater.download_installer(
                info["url"], progress=_progress)

        threading.Thread(target=_work, daemon=True).start()
        win.after(120, _poll)

    dl_btn.configure(command=_download)
    return win
