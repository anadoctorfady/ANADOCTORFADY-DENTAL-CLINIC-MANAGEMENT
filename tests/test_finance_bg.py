"""Finance background (ITEM 8, 2026-11-08): darker, low-glare surfaces
in both modes, with every finance text/background pair >= 4.5:1 WCAG.

Light mode is no longer near-white: bg #D8CFC0 (lum 0.630) replaces
Warm Sand #F6F1E9 (0.884) / panel #FFFFFF (1.000); panel #E3D9C8
(0.701) replaces white. Dark mode keeps the comfortable Warm Charcoal
bg with a slightly warmer panel. The old muted/accent/value colours
would have failed on the darker light bg, so the finance tokens carry
darkened text colours too (see src/config/theme.py FINANCE_*).
GUI test builds the real FinanceTab under Xvfb and skips gracefully
when no display is available (plain `run_tests.py` without Xvfb)."""
import re
import tkinter as tk

from src.config.theme import (LIGHT, DARK, TABLE, FINANCE_LIGHT,
                              FINANCE_DARK, finance_tokens,
                              finance_current)
from src.config.settings import get_theme_mode, set_theme_mode
from src.ui.rounded import RoundedButton

# Old (pre-ITEM-8) finance surfaces, locked in as the regression baseline.
OLD_LIGHT_BG, OLD_LIGHT_PANEL = "#F6F1E9", "#FFFFFF"
OLD_TABLE_FINANCE = "#FED7AA"
VALUE_KEYS = ("income", "expenses", "lab", "debts", "net")


def _lum(hexcol):
    r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = f(r), f(g), f(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(fg, bg):
    a, b = _lum(fg), _lum(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def test_finance_light_darker_than_old():
    """Light finance surfaces are visibly darker than the old glare:
    bg luminance 0.630 (< 0.70 threshold, was 0.884) and panel 0.701
    (was pure white 1.000); the card is darker than the old card too."""
    assert _lum(FINANCE_LIGHT["bg"]) < 0.70, FINANCE_LIGHT["bg"]
    assert _lum(FINANCE_LIGHT["bg"]) < _lum(OLD_LIGHT_BG)
    assert _lum(FINANCE_LIGHT["bg"]) < _lum(OLD_LIGHT_PANEL)
    assert _lum(FINANCE_LIGHT["panel"]) < _lum(OLD_LIGHT_PANEL)
    assert _lum(FINANCE_LIGHT["card"]) < _lum(LIGHT["card"])
    assert FINANCE_LIGHT["bg"] != LIGHT["bg"]
    assert FINANCE_LIGHT["panel"] != LIGHT["panel"]
    # Clinical Cost section shares finance styling via TABLE: its bright
    # peach #FED7AA is now muted warm sand (darker + desaturated).
    assert TABLE["finance"] != OLD_TABLE_FINANCE
    assert _lum(TABLE["finance"]) < _lum(OLD_TABLE_FINANCE)
    # ...while its existing text colours still pass on the new tint.
    assert _ratio("#6B5E53", TABLE["finance"]) >= 4.5
    assert _ratio("#000000", TABLE["finance"]) >= 4.5


def test_finance_dark_stays_dark():
    """Dark mode stays comfortable: every finance surface is dark."""
    for key in ("bg", "panel", "card"):
        assert _lum(FINANCE_DARK[key]) < 0.05, f"{key} {FINANCE_DARK[key]}"
    assert FINANCE_DARK["bg"] == DARK["bg"]  # Warm Charcoal kept


def _assert_pairs(tokens, mode):
    """Every finance text/background pair actually rendered >= 4.5:1."""
    for bg_key in ("bg", "panel", "card"):
        for fg_key in ("text", "muted", "accent"):
            r = _ratio(tokens[fg_key], tokens[bg_key])
            assert r >= 4.5, f"{mode}: {fg_key} on {bg_key}: {r:.2f}"
    for fg_key in ("danger",) + VALUE_KEYS:
        for bg_key in ("bg", "panel"):
            r = _ratio(tokens[fg_key], tokens[bg_key])
            assert r >= 4.5, f"{mode}: {fg_key} on {bg_key}: {r:.2f}"
    r = _ratio(tokens["btn_text"], tokens["accent"])
    assert r >= 4.5, f"{mode}: btn_text on accent: {r:.2f}"
    # Solid Lab button keeps white text on #5E5CE6 in both modes.
    assert _ratio("#FFFFFF", "#5E5CE6") >= 4.5


def test_finance_contrast_light():
    _assert_pairs(FINANCE_LIGHT, "light")


def test_finance_contrast_dark():
    _assert_pairs(FINANCE_DARK, "dark")


def test_finance_tokens_follow_mode():
    """finance_current() follows the theme mode; global tokens untouched."""
    prev = get_theme_mode()
    try:
        set_theme_mode("light")
        assert finance_current() == FINANCE_LIGHT
        assert finance_tokens(False) == FINANCE_LIGHT
        set_theme_mode("dark")
        assert finance_current() == FINANCE_DARK
        assert finance_tokens(True) == FINANCE_DARK
    finally:
        set_theme_mode(prev)
    assert LIGHT["bg"] == "#F6F1E9" and LIGHT["panel"] == "#EDE4D3"
    assert DARK["bg"] == "#1A1614"


class _StubApp:
    current_user = "fady"
    current_role = "admin"
    current_patient = None
    finance_gate = None


def _build_tab(mode):
    """FinanceTab in the requested theme; None when no display."""
    from src.ui.finance import FinanceTab
    prev = get_theme_mode()
    set_theme_mode(mode)
    try:
        root = tk.Tk()
    except tk.TclError:
        set_theme_mode(prev)
        return None, prev
    root.withdraw()
    try:
        tab = FinanceTab(tk.Frame(root), _StubApp())
        root.update_idletasks()
        return tab, prev
    except Exception:
        root.destroy()
        set_theme_mode(prev)
        raise


def _walk(widget):
    for w in widget.winfo_children():
        yield w
        yield from _walk(w)


def _check_labels_buttons(tab, mode, tokens):
    """Every rendered label/button in the tab reaches 4.5:1 fg vs bg."""
    for w in _walk(tab):
        if isinstance(w, (tk.Label, tk.Button)):
            if not str(w.cget("text")).strip():
                continue
            if isinstance(w, RoundedButton):
                # Rendered colours live in _bg/_fg (the PIL face): the
                # widget's own bg is the PARENT bg (transparent corners
                # show it), and configure() keeps fg there too, so
                # cget("bg")/cget("fg") do NOT describe what is drawn.
                fg, bg = str(w._fg), str(w._bg)
            else:
                fg, bg = str(w.cget("fg")), str(w.cget("bg"))
            assert re.fullmatch(r"#[0-9a-fA-F]{6}", fg), f"{mode}: {w} fg {fg!r}"
            assert re.fullmatch(r"#[0-9a-fA-F]{6}", bg), f"{mode}: {w} bg {bg!r}"
            r = _ratio(fg, bg)
            assert r >= 4.5, f"{mode}: {w.cget('text')!r} {fg} on {bg} = {r:.2f}"


def _check_tab(mode):
    tab, prev = _build_tab(mode)
    if tab is None:
        print(f"SKIP test_finance_tab_{mode} (no display)")
        return
    try:
        tokens = FINANCE_LIGHT if mode == "light" else FINANCE_DARK
        assert str(tab.cget("bg")) == tokens["bg"], f"{mode}: tab bg"
        # Summary cards sit on the finance panel with finance value colours.
        assert str(tab.cards["Total Income"].cget("bg")) == tokens["panel"]
        assert str(tab.cards["Total Income"].cget("fg")) == tokens["income"]
        assert str(tab.cards["Total Expenses"].cget("fg")) == tokens["expenses"]
        assert str(tab.cards["Total Lab"].cget("fg")) == tokens["lab"]
        assert str(tab.cards["Total Debts"].cget("fg")) == tokens["debts"]
        assert str(tab.cards["Net Income"].cget("fg")) == tokens["net"]
        # Every notebook sub-tab frame (Expenses/Lab/Debts/Centers/
        # Salaries) is painted with the finance panel - including
        # Salaries, which is built by salaries_view.py and recoloured.
        from tkinter import ttk
        nb = next(w for w in tab.winfo_children() if isinstance(w, ttk.Notebook))
        for tab_id in nb.tabs():
            frame = nb.nametowidget(tab_id)
            assert str(frame.cget("bg")) == tokens["panel"], \
                f"{mode}: {nb.tab(tab_id, 'text')} bg {frame.cget('bg')}"
        # Lock overlay + role overlays use the finance surfaces too.
        assert str(tab._lock.cget("bg")) == tokens["bg"]
        assert str(tab._doc_view.cget("bg")) == tokens["bg"]
        assert str(tab._nurse_view.cget("bg")) == tokens["bg"]
        _check_labels_buttons(tab, mode, tokens)
    finally:
        tab.master.destroy()
        set_theme_mode(prev)


def test_finance_tab_light():
    _check_tab("light")


def test_finance_tab_dark():
    _check_tab("dark")
