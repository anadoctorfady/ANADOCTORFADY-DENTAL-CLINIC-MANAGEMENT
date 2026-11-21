"""Round 24 (item 6): zebra on the LISTBOX surfaces -- template
picker, template manager and the clipboard-history panel (the
panel was the R24 fix: its refresh never striped). Helpers shared
from tests/test_r24_zebra_audit.py. Isolated DB, skips w/o display."""
import tkinter as tk

from src.models.database import set_setting
from tests.test_templates_edit import isolated_db
from tests.test_r24_zebra_audit import _assert_listbox_zebra


def test_zebra_template_and_clipboard_lists():
    """Listbox surfaces: template picker, template manager and the
    clipboard-history panel (the R24 fix) stripe alternately."""
    try:
        tk.Tk().destroy()
    except tk.TclError:
        print("SKIP zebra lists (no display)"); return
    with isolated_db():
        set_setting("theme_mode", "light")
        root = tk.Tk(); root.withdraw()
        try:
            from src.models.clipboard_history import add_clip
            for i in range(3):
                add_clip(f"zebra clip {i} text")
            from src.ui import phrase_picker
            win = phrase_picker.show_clipboard_panel(root)
            root.update_idletasks()
            boxes = []
            def _walk(w):
                from src.ui.rounded_lists import RoundedListbox
                if isinstance(w, RoundedListbox):
                    boxes.append(w)
                for ch in w.winfo_children():
                    _walk(ch)
            _walk(win)
            assert boxes, "clipboard listbox not found"
            _assert_listbox_zebra(boxes[0], False, "clipboard panel list")
            win.destroy()
            txt = tk.Text(root)
            win = phrase_picker.open_template_picker(root, "complaint", txt, "fady")
            root.update_idletasks()
            boxes = []
            _walk(win)
            assert boxes and boxes[0].listbox.size() >= 2
            _assert_listbox_zebra(boxes[0], False, "template picker list")
            win.destroy()
            from src.ui.template_manager import open_template_manager
            win = open_template_manager(root, "fady")
            root.update_idletasks()
            boxes = []
            _walk(win)
            assert boxes and boxes[0].listbox.size() >= 2
            _assert_listbox_zebra(boxes[0], False, "template manager list")
            win.destroy()
        finally:
            root.destroy()
