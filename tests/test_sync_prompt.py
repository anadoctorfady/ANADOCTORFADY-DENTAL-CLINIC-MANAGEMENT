"""Sync password prompt (2026-11-08): prompt_password() must return the
typed password on OK and None on Cancel. Regression: the function used
the typo'd name `resulth` (dict is `result`), so OK raised NameError
and Cancel raised NameError on return - Sync Now could never complete.
GUI tests skip with no display."""
from src.ui import sync_now_ui


def _drive_prompt(root, text, button_index):
    """Drive the sync password prompt from inside its wait_window loop:
    type `text` into its Entry and invoke button `button_index`
    (0 = OK/Sync, 1 = Cancel). Scheduled with after() before calling
    prompt_password, so it runs while the modal is open."""
    def _find(w, cls):
        out = []
        for c in w.winfo_children():
            if c.winfo_class() == cls:
                out.append(c)
            out += _find(c, cls)
        return out

    def _go():
        for w in root.winfo_children():
            if w.winfo_class() != "Toplevel":
                continue
            entries = _find(w, "Entry")
            buttons = _find(w, "Button")
            if entries and len(buttons) > button_index:
                entries[0].delete(0, "end")
                entries[0].insert(0, text)
                buttons[button_index].invoke()
                return

    root.after(150, _go)


def _prompt_root():
    """Withdrawn Tk root for the prompt tests; None with no display."""
    import tkinter as tk
    try:
        root = tk.Tk()
    except tk.TclError:
        return None
    root.withdraw()
    return root


def test_prompt_password_ok_returns_typed_password():
    """Regression (2026-11-08): prompt_password() used the typo'd name
    `resulth` (dict is `result`), so OK raised NameError and Cancel
    raised NameError on return - Sync Now could never complete."""
    root = _prompt_root()
    if root is None:
        return  # no display: skip GUI check
    try:
        _drive_prompt(root, "secret123", 0)
        pw = sync_now_ui.prompt_password(root, "fady")
        assert pw == "secret123", pw
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def test_prompt_password_cancel_returns_none():
    root = _prompt_root()
    if root is None:
        return  # no display: skip GUI check
    try:
        _drive_prompt(root, "secret123", 1)
        pw = sync_now_ui.prompt_password(root, "fady")
        assert pw is None, pw
    finally:
        try:
            root.destroy()
        except Exception:
            pass
