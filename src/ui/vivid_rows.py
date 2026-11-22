"""Round 40 (item 2): VIVID rotating row colours for the two
money-bearing lists — the unified clinical session table
(tree_history) and the Payments review (tree_fin).

Owner's words: the information rows must be in different colours,
NOT the app's basic colours, "to give the app life and make
payments easy to distinguish — every row a different colour from
the row before and after it (sky blue, violet, pink/rose...)".
Row backgrounds therefore cycle a 5-colour rotation, neighbours
NEVER repeat. The same colours serve BOTH themes with dark text.
Zebra striping elsewhere in the app is untouched — this module is
applied ONLY to the two lists. The vivid tag goes FIRST in a row's
tag list (zebra's rule), so meaning tags keep precedence for the
properties they set; the credit STATE colours (theme.credit_color)
live on the balance lines, independent of row backgrounds.

Round 41 (item 6) palette revision — owner feedback on the round-40
build: the pale pastels (83–92% lightness) read as SHADES OF ONE
ANOTHER on his Windows screen; the difference between neighbouring
rows must be CLEAR, not a gradient step. The rotation is now five
SATURATED hues at 56–71% lightness, ordered so neighbouring hues
sit >= 85 degrees apart on the colour wheel (sky 199 -> orange 27
-> green 142 -> hot pink 318 -> amber 43). Violet is deliberately
NOT a row colour any more: the selection owns violet (#7C3AED bg +
white text), so no row can be mistaken for it. Measured with
clinical_table_style.contrast_ratio: the dark text (#2C241D) sits
at 5.76–9.13:1 on every colour (>= 4.5 in both themes, identical
numbers — the colours do not change with the theme), and the
selection stands 2.15–3.41:1 in luminance off every row colour
plus >= 53 degrees of hue distance — the round-40 >= 4:1 luminance
bar is re-pinned to >= 2:1 + hue separation because saturated
mid-luminance colours cannot reach 4:1 against a deep-violet
selection by luminance alone; distinctness is carried by hue +
luminance + the selection's white text together. <200 lines."""
import tkinter.ttk as ttk

from src.config.theme import current

PALETTE = ("#38BDF8", "#FB923C", "#4ADE80", "#F472B6", "#FBBF24")
PALETTE_NAMES = ("sky blue", "orange", "green", "hot pink", "amber")
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
    st.configure(STYLE, background=th["list_bg"],
                 fieldbackground=th["list_bg"], foreground=th["text"],
                 rowheight=24, font=("Segoe UI", 9))
    st.configure(f"{STYLE}.Heading", background=th["card"],
                 foreground=th["text"])
    st.map(STYLE, background=[("selected", SELECT_BG)],
           foreground=[("selected", SELECT_FG)])
    return STYLE


def vivid_tree(tree):
    """Tag every current row vivid{position % 5} (tag FIRST, like
    zebra_tree) and (re)configure the tag colours. Called at the
    END of the two lists' fill routines."""
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
