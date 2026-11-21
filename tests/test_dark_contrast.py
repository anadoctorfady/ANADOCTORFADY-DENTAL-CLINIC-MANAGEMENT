"""Dark-mode contrast (CHANGE 2, 2026-11-07): labels on dark panels must
use the theme text token (>= 4.5:1 WCAG), never Tk's black default
(1.52:1 on the dark-brown patient panel). Light mode must stay exactly
as the owner approved (light-brown #E8DCC4 panel, dark text).

GUI tests build the real PatientForm under Xvfb and skip gracefully
when no display is available (plain `run_tests.py` without Xvfb)."""
import re
import tkinter as tk
from pathlib import Path

from src.config.theme import LIGHT, DARK
from src.config.settings import get_theme_mode, set_theme_mode
from src.ui.panel_paper import tinted_avg_hex

ROOT = Path(__file__).resolve().parent.parent
# settings_ui.py is owned by the parallel Sync-Now agent; sync_now_ui.py
# is that agent's file too - both are audited in the report, not here.
EXCLUDED = {"settings_ui.py", "sync_now_ui.py"}


def _lum(hexcol):
    r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = f(r), f(g), f(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(fg, bg):
    a, b = _lum(fg), _lum(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def test_contrast_ratios():
    """Theme text token passes 4.5:1 on every dark panel; light text
    passes on the light-brown patient panel; the old black default and
    the dark accent on the dark patient panel do NOT (why the fix)."""
    for bg in (DARK["patient_bg"], DARK["panel"], DARK["card"], DARK["bg"], DARK["list_bg"]):
        assert _ratio(DARK["text"], bg) >= 4.5, f"dark text on {bg}"
        assert _ratio(DARK["muted"], bg) >= 4.5, f"dark muted on {bg}"
    assert _ratio(DARK["accent"], DARK["panel"]) >= 4.5
    assert _ratio(LIGHT["text"], LIGHT["patient_bg"]) >= 4.5
    assert _ratio(LIGHT["text"], LIGHT["panel"]) >= 4.5
    assert _ratio(LIGHT["muted"], LIGHT["patient_bg"]) >= 4.5
    assert _ratio(LIGHT["ok"], LIGHT["bg"]) >= 4.5
    assert _ratio(DARK["ok"], DARK["bg"]) >= 4.5
    # The defect, locked in as a regression tripwire:
    assert _ratio("#000000", DARK["patient_bg"]) < 2.0  # was 1.52:1
    assert _ratio(DARK["accent"], DARK["patient_bg"]) < 4.5  # 4.37:1
    assert _ratio(LIGHT["accent"], LIGHT["patient_bg"]) >= 4.5  # 5.02:1 since round 16 (accent darkened when white left)


def _check_widget_labels(widget, where, skip=()):
    """Every text label/button-ish widget must reach 4.5:1 fg vs bg."""
    for w in widget.winfo_children():
        _check_widget_labels(w, where, skip)
        if w in skip:
            continue
        if isinstance(w, (tk.Label, tk.Radiobutton, tk.Checkbutton)):
            if w.cget("image") or not str(w.cget("text")).strip():
                continue
            fg, bg = str(w.cget("fg")), str(w.cget("bg"))
            assert re.fullmatch(r"#[0-9a-fA-F]{6}", fg), f"{where}: {w} fg {fg!r}"
            assert re.fullmatch(r"#[0-9a-fA-F]{6}", bg), f"{where}: {w} bg {bg!r}"
            assert _ratio(fg, bg) >= 4.5, f"{where}: {w.cget('text')!r} {fg} on {bg}"


def _check_light_bg_buttons(widget, where):
    """Buttons on light backgrounds (dental-chart teeth keep pastel
    backgrounds in both modes) must have dark text in both modes."""
    for w in widget.winfo_children():
        _check_light_bg_buttons(w, where)
        if isinstance(w, tk.Button):
            fg, bg = str(w.cget("fg")), str(w.cget("bg"))
            if (re.fullmatch(r"#[0-9a-fA-F]{6}", fg)
                    and re.fullmatch(r"#[0-9a-fA-F]{6}", bg)
                    and _lum(bg) > 0.5):
                assert _ratio(fg, bg) >= 4.5, f"{where}: button {w.cget('text')!r} {fg} on {bg}"


def _build_form(mode):
    """PatientForm in the requested theme; None when no display."""
    from src.ui.patient_form import PatientForm
    prev = get_theme_mode()
    set_theme_mode(mode)
    try:
        root = tk.Tk()
    except tk.TclError:
        set_theme_mode(prev)
        return None, prev
    root.withdraw()

    class Stub:
        lang = "en"
        current_patient = None
        def on_teeth_select(self, *a): pass
        def print_pdf(self, *a): pass
        def load_patients(self): pass
        def select_patient(self, *a): pass

    try:
        form = PatientForm(root, Stub())
        root.update_idletasks()
        return form, prev
    except Exception:
        root.destroy()
        set_theme_mode(prev)
        raise


def test_patient_form_labels_dark():
    form, prev = _build_form("dark")
    if form is None:
        print("SKIP test_patient_form_labels_dark (no display)")
        return
    try:
        toks = DARK
        _check_widget_labels(form, "dark patient form")
        _check_light_bg_buttons(form, "dark patient form")
        # Every label on the details panel uses the text token exactly.
        form_labels = []

        def collect(widget):
            for w in widget.winfo_children():
                collect(w)
                if isinstance(w, tk.Label) and str(w.cget("bg")) == toks["patient_bg"]:
                    form_labels.append(w)
        collect(form)
        assert len(form_labels) >= 16, f"expected >=16 labels on patient panel, got {len(form_labels)}"
        for w in form_labels:
            assert str(w.cget("fg")) == toks["text"], f"dark: {w.cget('text')!r} fg={w.cget('fg')}"
    finally:
        form.master.destroy()
        set_theme_mode(prev)


def test_patient_form_labels_light():
    """Light mode: field labels use the light text token, value
    labels keep their original accent / muted colors; their bg is
    the tinted panel average (round 13 item 5 ext), not raw #E8DCC4."""
    form, prev = _build_form("light")
    if form is None:
        print("SKIP test_patient_form_labels_light (no display)")
        return
    try:
        # Light accent on the light panel is 5.40:1 since round 16
        # (accent darkened when white left); the hijri/age labels
        # keep their original colours and are checked separately below,
        # not by the 4.5:1 sweep.
        _check_widget_labels(form, "light patient form",
                             skip=(form.lbl_hijri, form.lbl_age, form.lbl_age_h))
        _check_light_bg_buttons(form, "light patient form")
        assert str(form.lbl_hijri.cget("fg")) == LIGHT["accent"]
        assert str(form.lbl_age.cget("fg")) == LIGHT["muted"]
        assert str(form.lbl_age_h.cget("fg")) == LIGHT["muted"]
        assert str(form.lbl_hijri.cget("bg")) == tinted_avg_hex(LIGHT["patient_bg"], 0.25)
    finally:
        form.master.destroy()
        set_theme_mode(prev)


def _join_calls(lines):
    """Yield (start_line, joined_call_text) for each tk widget call."""
    i = 0
    while i < len(lines):
        ln = lines[i]
        if re.search(r"tk\.(Label|Checkbutton|Radiobutton)\(|tk\.LabelFrame\(", ln):
            buf, j, depth = ln, i, ln.count("(") - ln.count(")")
            while depth > 0 and j + 1 < len(lines):
                j += 1
                buf += " " + lines[j].strip()
                depth += lines[j].count("(") - lines[j].count(")")
            yield i + 1, buf
            i = j
        i += 1


def test_no_bare_labels_in_source():
    """Static audit guard: no text widget on a theme panel may rely on
    Tk's black default fg. TABLE[...] tints are light in both modes,
    so black text there is fine; image-only labels have no text."""
    for p in sorted((ROOT / "src" / "ui").glob("*.py")):
        if p.name in EXCLUDED:
            continue
        for lineno, call in _join_calls(p.read_text(encoding="utf-8").splitlines()):
            if "TABLE[" in call or "image=" in call:
                continue
            if re.search(r'bg=(t\[|current\(\)\[|parent\[)', call):
                assert "fg=" in call, f"{p.name}:{lineno}: no fg on theme bg: {call[:100]}"
        # No hardcoded dark-green status colour left (now the "ok" token).
        assert 'fg="#2E7D32"' not in p.read_text(encoding="utf-8"), p.name
    # Hardcoded #6B5E53 survives only on light TABLE tints (>= 4.6:1).
    for name in ("clinical_finance.py", "phrase_picker.py"):
        src = (ROOT / "src" / "ui" / name).read_text(encoding="utf-8")
        for m in re.finditer(r'fg="#6B5E53"', src):
            ctx = src[max(0, m.start() - 200):m.start()]
            assert "TABLE[" in ctx or "parent[" in ctx, f"{name}: #6B5E53 off a light tint"
