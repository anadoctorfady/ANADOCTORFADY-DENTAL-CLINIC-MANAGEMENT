"""UI font policy (Round 51 introduced Amiri; Round 56 REVERTED it).

Owner verdict (2026-11-25, AR-vs-EN screenshots of patient #5):
the Arabic UI was much TALLER than English -- Amiri's linespace
is ~30% taller than Segoe UI at the same point size (round 51
measured Amiri 10pt linespace 36px vs Segoe 28px at tk scaling
2.0), so every AR row, pill and tab was taller and less of the
dental chart fitted in Arabic. The owner authorised the revert:
"if it is the cause, no problem if you go back to the old font."

So the Arabic UI is back to the pre-round-51 font: Segoe UI as
the UI family in BOTH languages; Arabic glyphs render through
the system's normal fallback, as they did before round 51.
Amiri registration is DISABLED (amiri_register returns False
and never calls AddFontResourceExW) and amiri_available()
always returns False, so no widget, style or chart ever swaps
to Amiri -- on any machine, including one where Amiri happens
to be installed system-wide. The bundled Amiri TTFs were
removed from assets/fonts/ in this round (nothing references
them any more). PDFs keep their embedded Noto Naskh font
(unchanged). The swap machinery (tree walk, style override)
was deleted with the revert; apply_ui_fonts() is now a no-op
kept as the font-policy seam for the shell's call sites.

CRITICAL GUARD (the round-50 clipping must not come back):
row heights are derived from the MEASURED linespace of the
font that actually renders the Arabic text -- the UI font as
Tk resolves it, plus the rendered height of an Arabic sample
drawn in that font (arabic_linespace) -- never from a
hardcoded 24 and never from Segoe's metrics alone.
tree_rowheight() in Arabic mode is max(24, arabic_linespace
+ 8). On this VM that measures 18px at 9pt (Segoe UI resolves
to Noto Sans; the Arabic sample's canvas bbox is 18px too, and
a pixel ink check puts the fallback glyphs' real ink at 14px
at 10pt -- inside the 20px line), so AR rows are 26px against
EN 24px, not the Amiri 31px. On Windows the fallback is the
system's (most likely Segoe UI Arabic, else Tahoma via
FontLink) -- both within ~1-2px of Segoe UI at the same size,
unlike Amiri's +28% -- but the final no-clipping confirmation
is the owner's screenshots after building (see REVIEW.md).
"""
import tkinter as tk
import tkinter.font as tkfont

FAMILY = "Amiri"  # historic name; the family is NOT used any more (R56)
UI_FAMILY = "Segoe UI"
_AR_SAMPLE = "العربية 123 تجربة"
_LS_CACHE = {}
# Registration + availability live in amiri_register.py (R56:
# both hard-disabled); re-exported so amiri.amiri_available
# and amiri._register_private keep working for callers/tests.
from src.ui.amiri_register import amiri_available, _register_private  # noqa: E402,F401


def note_build_family(app):
    """R56: always None -- no Amiri any more, so widgets are
    born in Segoe UI in both languages (RoundedButton reads
    this at creation)."""
    try:
        app._ui_family = None
    except Exception:
        pass


def arabic_linespace(size=9, root=None):
    """Measured linespace (px) of the font that renders Arabic
    text in the UI: the UI font's resolved linespace, and the
    rendered height of an Arabic sample drawn in that font on a
    canvas (the fallback glyphs as Tk draws them). The max of
    the two, so a fallback taller than the base font is caught.
    Cached per (size, tk scaling)."""
    try:
        r = root or tk._default_root
        scaling = r.tk.call("tk", "scaling") if r is not None else 1.0
    except Exception:
        r, scaling = None, 1.0
    key = (size, round(float(scaling), 3))
    if key in _LS_CACHE:
        return _LS_CACHE[key]
    try:
        ls = tkfont.Font(family=UI_FAMILY, size=size).metrics("linespace")
    except Exception:
        ls = 18
    if r is not None:
        try:
            cv = tk.Canvas(r, width=16, height=16)
            item = cv.create_text(0, 0, text=_AR_SAMPLE,
                                  font=(UI_FAMILY, size), anchor="nw")
            bb = cv.bbox(item)
            cv.destroy()
            if bb:
                ls = max(ls, bb[3] - bb[1])
        except Exception:
            pass
    _LS_CACHE[key] = ls
    return ls


def row_font(app, size=9, *styles):
    """Font tuple for tree row tags: Segoe UI in both languages
    since the Round 56 Amiri revert (was Amiri in Arabic mode)."""
    return (UI_FAMILY, size, *styles)


def _saved_lang():
    try:
        from src.models.database import get_setting
        return get_setting("language", "en") or "en"
    except Exception:
        return "en"


def tree_font(size=9):
    """The font every ttk tree style must carry for the SAVED
    language: Segoe UI in both languages since the Round 56
    Amiri revert."""
    return (UI_FAMILY, size)


def tree_rowheight(size=9, root=None):
    """The ttk Treeview row height that fits the CURRENT tree
    font: 24 in English; in Arabic mode, the MEASURED Arabic
    linespace + 8 (min 24). R56 guard: the linespace comes from
    arabic_linespace() -- the font that actually renders the
    Arabic text -- not from a literal 24 and not from Segoe
    UI's metrics alone (the round-50 clipping root cause was a
    literal 24 that did not fit the real Arabic line)."""
    if _saved_lang() == "ar":
        return max(24, arabic_linespace(size, root) + 8)
    return 24


def apply_ui_fonts(app, root=None):
    """Round 56: a no-op -- the UI stays in Segoe UI in both
    languages. Kept as the font-policy seam so the shell's
    call sites (build, rebuild, dialog) need no change."""
    return None
