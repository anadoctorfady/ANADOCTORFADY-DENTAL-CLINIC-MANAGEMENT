"""Warm Sand Design System v1.0 - tokens only. <150 lines."""
LIGHT = {
    "bg": "#F6F1E9", "panel": "#EDE4D3", "card": "#F2EBDD",
    "text": "#2C241D", "muted": "#6B5E53", "accent": "#8A4A22",
    "border": "#E3D8CC", "patient_bg": "#E8DCC4", "ok": "#2E7D32", "ok": "#2E7D32",
    "list_bg": "#F6F1E9", "header1": "#7C3AED",
    "header2": "#EC4899", "header3": "#F97316",
}
DARK = {
    "bg": "#1A1614", "panel": "#26211E", "card": "#332C28",
    "text": "#F5F0EB", "muted": "#A3968A", "accent": "#D97736",
    "border": "#453D37", "patient_bg": "#3E2723", "ok": "#4ADE80", "ok": "#4ADE80",
    "list_bg": "#332C28", "header1": "#8B5CF6",
    "header2": "#EC4899", "header3": "#F97316",
}
# Finance surfaces (ITEM 8, 2026-11-08): darker, low-glare, eye-friendly.
# Round 16 (2026-11-11, NO WHITE): the MAIN light panel is warm sand
# #EDE4D3 (lum 0.79) and card #F2EBDD (0.83) - never #FFFFFF. The old
# light accent #A85F33 was only 4.83:1 on white and would fall to
# 3.83:1 on the sand panel, so it darkened (same brown hue) to #8A4A22:
# 5.40:1 on the panel, 6.06:1 on bg, 6.81:1 white-on-accent for buttons.
# Light mode is NO LONGER near-white: bg #D8CFC0 (lum 0.630 vs Warm Sand
# #F6F1E9 0.884 / panel #EDE4D3 0.79) and panel #E3D9C8 (0.701) are muted
# warm taupe-sand. Because a darker bg lowers contrast, the finance text
# colours are darkened too (muted #54483C, accent #7A3F16, value colours
# #991B1B/#4338CA/#9A3412/#065F46) so EVERY pair stays >= 4.5:1 - the old
# muted #6B5E53 (4.06:1) and accent #A85F33 (3.13:1) would have failed
# on the new bg. Dark mode keeps the comfortable Warm Charcoal bg and a
# slightly warmer panel #2B251F; its accent #E07B39 (not #D97736) is the
# one orange that also passes 4.5:1 on the card #332C28 (4.61:1).
# btn_text is the label colour on solid accent buttons: white in light
# mode (8.23:1 on #7A3F16), near-black warm in dark mode (5.73:1 on
# #E07B39) - white on the dark accent would be only ~2.9:1.
# R31: sel_bg/sel_fg are the expense-picker SELECTED chip pair only.
# Light reuses accent/btn_text (8.23:1). The dark accent caps at
# 5.73:1 with ANY foreground (6.83:1 even with pure black), so the
# dark chip uses vivid amber #F59E0B + the same near-black text:
# 7.94:1 by formula, verified from rendered pixels in round 31.
FINANCE_LIGHT = {
    "bg": "#D8CFC0", "panel": "#E3D9C8", "card": "#EFE7D8",
    "text": "#2C241D", "muted": "#54483C", "accent": "#7A3F16",
    "border": "#B8A88F", "danger": "#991B1B", "btn_text": "#FFFFFF",
    "sel_bg": "#7A3F16", "sel_fg": "#FFFFFF",
    "income": "#7A3F16", "expenses": "#991B1B", "lab": "#4338CA",
    "debts": "#9A3412", "net": "#065F46",
}
FINANCE_DARK = {
    "bg": "#1A1614", "panel": "#2B251F", "card": "#332C28",
    "text": "#F5F0EB", "muted": "#A3968A", "accent": "#E07B39",
    "border": "#453D37", "danger": "#F87171", "btn_text": "#241A12",
    "sel_bg": "#F59E0B", "sel_fg": "#241A12",
    "income": "#E07B39", "expenses": "#F87171", "lab": "#A5B4FC",
    "debts": "#FB923C", "net": "#34D399",
}
def finance_tokens(dark=False):
    """Finance-area tokens for the requested theme mode."""
    return FINANCE_DARK if dark else FINANCE_LIGHT
def finance_current():
    """Finance-area tokens for the current theme mode."""
    return finance_tokens(is_dark())
SPACING = [4, 8, 12, 16, 24, 32]
RADIUS_CARD, RADIUS_BTN = 16, 12
RADIUS_FIELD, RADIUS_TEXT = 14, 16  # rounded input fields / multi-line text
# Rounded corners (Round 12, Item B): radii per surface. Tkinter
# has no native rounded corners; src/ui/rounded.py renders them
# with PIL. History: original scale CARD/PANEL 12, TABLE/TEXT/
# ICON 10, FIELD/BTN 8. Round 28 REDUCED it (8/6) on a MISREADING
# of the owner's request. Round 30 RAISED it ABOVE the originals
# per the owner's explicit correction (CARD/PANEL 16, others 12).
# Round 31 (owner live-use feedback): the tables/fields he TYPES
# in go rounder still -- TABLE/TEXT 16, FIELD 14; CARD/PANEL 16
# and BTN/ICON 12 unchanged.
RADIUS_PANEL = 16  # cards / panels (== RADIUS_CARD)
RADIUS_TABLE = 24  # rounded wrapper around a ttk Treeview (R43: 16 -> 24, owner wants tables MORE rounded; corners antialiased in rounded.py)
RADIUS_ICON = 12   # icon buttons / calendar cells
BTN_H, INPUT_H = 40, 38
FONT = ("system-ui", "Segoe UI", "Tahoma", "Arial", "sans-serif")
FONT_UI = ("Segoe UI", 10)
FONT_H = ("Segoe UI", 14, "bold")
FONT_BODY = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
# iOS27 gradient header + Warm Sand base
GRADIENT = ("#7C3AED", "#EC4899", "#F97316")
# Patient names cycle (iOS27 vivid) - same six hues in the SAME order in
# both modes: darker shades in light mode, lighter shades in dark mode.
# Every colour is >= 4.5:1 WCAG on its own mode's list background
# (owner-approved 2026-11-07; verified in tests/test_name_colors.py).
NAME_COLORS_LIGHT = ["#5B21B6", "#BE185D", "#C2410C", "#0F766E", "#9D174D", "#047857"]
NAME_COLORS_DARK = ["#A78BFA", "#F472B6", "#FB923C", "#2DD4BF", "#F9A8D4", "#34D399"]
NAME_COLORS = NAME_COLORS_LIGHT  # legacy alias = light palette
def name_colors(dark=False):
    """Rotating patient-name palette for the requested theme mode."""
    return NAME_COLORS_DARK if dark else NAME_COLORS_LIGHT
# Round 21 (item 1): debtor / health-alert red for patient names and
# the Diseases / Allergies lines. Each is >= 4.5:1 WCAG on its mode's
# list background (asserted in tests/test_r21_red_zebra.py).
DEBT_RED = {"light": "#B91C1C", "dark": "#F87171"}
def debt_red(dark=False):
    """The round-21 alert red for the requested theme mode."""
    return DEBT_RED["dark" if dark else "light"]
# Round 38: patient-CREDIT text colour (advance payments — the
# clinic owes the patient). A teal/green deliberately distinct
# from DEBT_RED and from the unpaid amber (#F59E0B). Each value is
# >= 4.5:1 WCAG on the surfaces it labels: the patient panel
# (#EDE4D3 light / #26211E dark), the finance section (#E5DAC6
# light / #92400E dark) and the main backgrounds; asserted in
# tests/test_r38_credit.py. The alert STRIP uses a solid teal
# block instead (patient_alerts.CREDIT_BG, white text, 5.47:1).
CREDIT = {"light": "#065F46", "dark": "#5EEAD4"}
def credit_color(dark=False):
    """The round-38 patient-credit colour for the requested mode."""
    return CREDIT["dark" if dark else "light"]
# Round 21 (item 6): zebra striping for multi-row tables/lists --
# two alternating row backgrounds per mode. Light: warm paper
# tones under the #2C241D text. Dark (item 3): deep amber-browns
# from the Total cost box family (#92400E), darkened for large
# areas, under the #F5F0EB text -- the cost boxes' treatment.
ZEBRA = {"light": ("#FBF6EC", "#F1E7D0"), "dark": ("#4A2C14", "#33200F")}
def zebra_colors(dark=False):
    """The (even, odd) zebra row backgrounds for the mode."""
    return ZEBRA["dark" if dark else "light"]
# Round 21 (item 9): entry-field border colour -- clearly visible
# against the panel in both modes (the old 1px theme border,
# #E3D8CC on #EDE4D3, was nearly invisible). Focus keeps the
# accent colour at a heavier width instead.
FIELD_BORDER = {"light": "#7A3F16", "dark": "#C9BBA6"}
def field_border(dark=False):
    """The round-21 entry border colour for the mode."""
    return FIELD_BORDER["dark" if dark else "light"]
# Per-table tints (warm family only since 2026-11-07 - no pink/lavender
# backgrounds remain anywhere in the app; see owner correction)
TABLE = {
    "complaint": "#FDE68A", "diagnosis": "#FFEDD5",
    "procedure": "#A7F3D0", "finance": "#E5DAC6",
    "appointment": "#DBEAFE", "expense": "#E7E5E4",
}
# NOTE (ITEM 8): TABLE["finance"] was bright peach #FED7AA (lum 0.726);
# it is now muted warm sand #E5DAC6 (lum 0.709) - same darker, low-glare
# family as the finance tab, applied to the clinical Cost section WITHOUT
# editing clinical_finance.py (it reads this token). #6B5E53 still passes
# 4.5:1 on it (4.53:1), as does default black text (15.18:1).
def tokens(dark=False):
    return DARK if dark else LIGHT
def get_tokens(mode):
    """Tokens by mode name: 'light' | 'dark'."""
    return DARK if mode == "dark" else LIGHT
def is_dark():
    try:
        from src.config.settings import get_setting
        return get_setting("theme_mode", "light") == "dark" or get_setting("dark_mode", "0") == "1"
    except Exception:
        return False
def mode():
    return "dark" if is_dark() else "light"
def current():
    return tokens(is_dark())
def tree_style(name, t=None):
    """Named ttk Treeview style in main-theme colors.

    The global "Treeview" style is set (in shell.py) to the main theme
    background (Warm Sand / Warm Charcoal) - since 2026-11-07 no pink or
    violet wash remains anywhere in the app. Tabs use a named style
    instead, so the global style is never touched.
    Pass t=finance_tokens() for the darker finance surfaces (ITEM 8).
    """
    import tkinter.ttk as _ttk
    from src.ui.amiri import tree_font, tree_rowheight
    t = t or current()
    st = _ttk.Style()
    st.configure(f"{name}.Treeview", background=t["panel"],
                 fieldbackground=t["panel"], foreground=t["text"],
                 rowheight=tree_rowheight(), font=tree_font())
    st.configure(f"{name}.Treeview.Heading", background=t["card"],
                 foreground=t["text"])
    return f"{name}.Treeview"
def notebook_style(name, t=None):
    """Named ttk Notebook style in main-theme colors (tab bar = bg).
    Pass t=finance_tokens() for the darker finance surfaces (ITEM 8)."""
    import tkinter.ttk as _ttk
    t = t or current()
    st = _ttk.Style()
    st.configure(f"{name}.TNotebook", background=t["bg"], borderwidth=0)
    st.configure(f"{name}.TNotebook.Tab", background=t["panel"],
                 foreground=t["text"], padding=(10, 4))
    st.map(f"{name}.TNotebook.Tab",
           background=[("selected", t["panel"]), ("!selected", t["card"])],
           foreground=[("selected", t["accent"]), ("!selected", t["text"])])
    return f"{name}.TNotebook"
