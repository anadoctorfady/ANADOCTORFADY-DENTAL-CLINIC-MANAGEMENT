"""Vivid rotating row colours for every row-based table/list.

Owner's words (round 40): the information rows must be in different
colours, NOT the app's basic colours, "to give the app life and make
payments easy to distinguish — every row a different colour from the
row before and after it". Round 43 extended the rotation from the
two money lists to EVERY table/list + the thumbnail grids (zebra.py
delegates here). Meaning FOREGROUNDS survive: ttk tag precedence
follows tag CREATION order (probed 2026-11-22), and every meaning
tag in the app is configured before the first striping call on its
tree; the vivid tag goes FIRST in a row's tag list, so meaning tags
keep precedence for the properties they set. The same colours serve
BOTH themes with dark text (#2C241D).

Round 48 (owner override 2026-11-23 14:39, superseding his round-41
saturation feedback and his round-47 violet approval of the same
day): the palette is EXACTLY the five round-40 colours visible in
gallery shot 137 — no colour added, none substituted — REORDERED
so no two tonally-close colours are ever neighbours. The saturated
round-41/47 set and the round-47 violet are withdrawn at his word.
RECOVERY: no hex list survived in the round-40 gate artifacts, so
the five were pixel-sampled with PIL from shots 137/138/139 (row
bands; identical values in all three): sky blue #BAE6FD, lavender
#DDD6FE, pink #FBCFE8, green #BBF7D0, orange #FED7AA.
REORDER: all 12 distinct 5-cycles were brute-forced with colorsys
hues (blue 200.6, orange 32.1, lavender 250.5, green 141.0, pink
325.9); the adopted cycle — blue -> orange -> lavender -> green ->
pink — maximizes the minimum adjacent hue gap at 109.5 degrees.
Adjacent gaps INCLUDING the pink -> blue wrap: 168.5 / 141.6 /
109.5 / 175.1 / 125.3. The set's two closest colours (blue and
lavender, 49.9 degrees apart) are NOT neighbours in this cycle.
Dark text measures 10.98–12.58:1 on the five (>= 4.5 by a wide
margin).
SELECTION DISTINCTNESS, stated honestly for round 48: against the
selection (#7C3AED bg + white text, hue 262.1) every row colour
stands 4.10–4.70:1 in luminance — beyond even the old round-40
>= 4:1 reading. Four colours also sit 61.5–130.0 degrees from the
selection hue, but LAVENDER sits only 11.6 degrees from it, so the
round-41 ">= 50 degrees of hue" clause does NOT hold for lavender;
that is recorded here, not hidden. Distinctness over a lavender
row is carried by the 4.10:1 luminance depth difference plus
INVERTED text (white on the selection, dark on every row): a
selected row — deep saturated violet, white text — cannot be
mistaken for an unselected one — pale lavender, dark text."""
import tkinter.ttk as ttk

from src.config.theme import current

PALETTE = ("#BAE6FD", "#FED7AA", "#DDD6FE", "#BBF7D0", "#FBCFE8")
PALETTE_NAMES = ("sky blue", "orange", "lavender", "green", "pink")
TEXT_ON_VIVID = "#2C241D"
SELECT_BG = "#7C3AED"  # deep iOS27 violet: the defined selection
SELECT_FG = "#FFFFFF"
STYLE = "Vivid.Treeview"
_TAGS = tuple(f"vivid{i}" for i in range(len(PALETTE)))


def palette():
    """The rotating row backgrounds, in rotation order."""
    return PALETTE


def row_tag(index):
    """The vivid tag for the row at display position `index`."""
    return _TAGS[index % len(_TAGS)]


def ensure_vivid_style():
    """(Re)configure the named ttk style for the vivid trees from
    the CURRENT theme tokens + the defined selection colours.
    Called at tree build time; the UI rebuilds on theme toggle,
    so the style is refreshed with the theme."""
    th = current()
    st = ttk.Style()
    from src.ui.amiri import tree_font, tree_rowheight
    st.configure(STYLE, background=th["list_bg"],
                 fieldbackground=th["list_bg"], foreground=th["text"],
                 rowheight=tree_rowheight(), font=tree_font())
    st.configure(f"{STYLE}.Heading", background=th["card"],
                 foreground=th["text"])
    st.map(STYLE, background=[("selected", SELECT_BG)],
           foreground=[("selected", SELECT_FG)])
    return STYLE


def vivid_tree(tree):
    """Tag every current row vivid{position % len(PALETTE)} (tag
    FIRST, like zebra_tree) and (re)configure the tag colours. Called at the
    END of each list's fill routine."""
    try:
        for i, bg in enumerate(PALETTE):
            tree.tag_configure(_TAGS[i], background=bg,
                               foreground=TEXT_ON_VIVID)
        for i, iid in enumerate(tree.get_children("")):
            tags = [tg for tg in tree.item(iid, "tags")
                    if tg not in _TAGS]
            tree.item(iid, tags=tuple([row_tag(i)] + tags))
    except Exception:
        pass


def vivid_listbox(lb):
    """Round 43: the same rotation for tk.Listbox surfaces (picker
    and manager lists, picker popups, appointment day/slot lists).
    A RoundedListbox is unwrapped to its inner Listbox. Selection
    colours are set per row so the violet selection stands off
    every palette colour."""
    try:
        lb = getattr(lb, "listbox", lb)
        lb.configure(selectbackground=SELECT_BG,
                     selectforeground=SELECT_FG)
        for i in range(lb.size()):
            lb.itemconfigure(i, background=PALETTE[i % len(PALETTE)],
                             foreground=TEXT_ON_VIVID,
                             selectbackground=SELECT_BG,
                             selectforeground=SELECT_FG)
    except Exception:
        pass
