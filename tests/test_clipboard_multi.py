"""Phase 2: clipboard multi-copy / multi-paste for clinical tables."""
from src.models.clipboard_history import (add_clip, clear_clips, copy_row_text,
    get_history, list_clips, multi_paste, multi_paste_all)
from src.ui.clipboard_picker import (CLIPBOARD_BINDING, bind_clipboard_picker,
    open_clipboard_picker, paste_items_into)
from src.ui.clinical import ClinicalTab
def test_history_stores_items():
    clear_clips()
    assert add_clip("MULTI first item") is True
    assert add_clip("MULTI second item") is True
    assert add_clip("MULTI third item") is True
    assert get_history() == ["MULTI third item", "MULTI second item", "MULTI first item"]
    assert [r["text"] for r in list_clips()] == get_history()
    for i in range(25):
        add_clip(f"MULTI bulk {i:02d}")
    assert len(get_history()) == 20  # picker/history cap
    assert len(list_clips()) == 20
    assert get_history()[0] == "MULTI bulk 24"  # newest first
    clear_clips(); assert get_history() == []
def test_multi_paste_order():
    clear_clips()
    add_clip("MULTI paste one"); add_clip("MULTI paste two"); add_clip("MULTI paste three")
    hist = get_history()
    assert hist == ["MULTI paste three", "MULTI paste two", "MULTI paste one"]
    second, first = hist[1], hist[2]  # 2nd newest, then 1st (oldest)
    assert multi_paste([second, first]) == "MULTI paste two\nMULTI paste one"
    assert multi_paste_all() == "\n".join(hist)  # paste-all: history order
    assert multi_paste([]) == "" and multi_paste(["  ", "x"]) == "x"
    clear_clips()
def test_copy_row():
    clear_clips()
    assert copy_row_text("MULTI row | 2026-11-07 | filling") is True
    assert "MULTI row | 2026-11-07 | filling" in get_history()
    assert copy_row_text("MULTI row | 2026-11-07 | filling") is True  # re-copy moves to top
    assert get_history()[0] == "MULTI row | 2026-11-07 | filling"
    assert len([t for t in get_history() if t.startswith("MULTI row")]) == 1  # deduped
    assert copy_row_text("  ") is None and copy_row_text("x") is None
    clear_clips()
def test_picker_available_in_fields():
    # Function-level checks (no GUI needed): picker + binding exist.
    assert CLIPBOARD_BINDING == "<Control-Shift-V>"
    assert callable(open_clipboard_picker) and callable(bind_clipboard_picker)
    assert callable(paste_items_into)
    for name in ("show_clipboard_picker", "load", "add", "add_fin"):
        assert callable(getattr(ClinicalTab, name)), name
    # Headless GUI check: skips gracefully when no display is available.
    try:
        import tkinter as tk
        root = tk.Tk()
    except Exception:
        return  # no display (e.g. CI) — function-level checks above stand
    try:
        root.withdraw()
        class FakeApp:
            current_patient = None; current_user = "fady"
            def chart_teeth(self): return []
            def refresh_clinical(self): pass
        tab = ClinicalTab(root, FakeApp())
        tab.pack()
        root.update_idletasks()
        for name in ("complaint", "symptom", "diagnosis", "procedure",
                     "sess_total", "cost_paid", "notes"):  # R38: the payment entry has no Total box; the session entry's total is "sess_total"
            assert name in tab.clipboard_fields, f"no clipboard field: {name}"
            w = tab.clipboard_fields[name]
            assert w.bind(CLIPBOARD_BINDING), f"no Ctrl+Shift+V on {name}"
        # Round 21 (item 5): the separate "(Optional)" notes section
        # is REMOVED; the templated visit Notes is the only notes
        # surface and owns the "notes" clipboard field.
        assert not hasattr(tab, "notes_section")
        assert tab.clipboard_fields["notes"] is tab.txt_visit_note
        assert tab.scans_frame is not None  # scans tab present after X-Rays
        # Item 5 redesign: no specialty picker, no copy-row buttons -
        # one small template-picker button per field, clipboard silent.
        assert not hasattr(tab, "specialty_picker")
        assert not hasattr(tab, "get_specialty")
        assert set(tab.picker_buttons) == {"complaint", "symptom", "diagnosis", "procedure"}
        import tkinter as _tk
        def _walk(w):
            yield w
            for ch in w.winfo_children():
                yield from _walk(ch)
        for w in _walk(tab):
            if isinstance(w, _tk.Button):
                assert "Copy row" not in str(w.cget("text")), w.cget("text")
                assert "copy" not in str(w.cget("text")).lower(), w.cget("text")
        # Picker actually pastes selected items one per line into a field.
        tab.txt_complaint.delete("1.0", tk.END)
        assert paste_items_into(tab.txt_complaint, ["line A", "line B"]) is True
        assert tab.txt_complaint.get("1.0", tk.END).strip() == "line A\nline B"
    finally:
        try:
            root.destroy()
        except Exception:
            pass
