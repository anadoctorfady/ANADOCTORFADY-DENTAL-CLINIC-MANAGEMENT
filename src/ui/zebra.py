"""Zebra striping for multi-row tables/lists (round 21 item 6).

Every multi-row Treeview/list gets two alternating row
backgrounds (theme.zebra_colors: warm paper tones in light mode,
deep cost-box browns in dark mode -- item 3). The helpers are
called at the END of each fill routine:

- zebra_tree(tree): (re)tags every current row zebra0/zebra1 by
  position. The zebra tag is placed FIRST in the row's tag list,
  so meaning tags applied later (patient-name colours, the red
  "debt" tag, appointment attendance colours) keep precedence
  for the properties they set -- the zebra tag sets ONLY the
  background. Selection highlighting comes from the ttk style
  and stays distinguishable (asserted in the round-21 test).
- zebra_listbox(lb): per-row background via itemconfigure for
  plain tk.Listbox surfaces (template picker/manager lists).

Colours are (re)configured on every call, so a theme rebuild
(fresh widgets) and a mode switch both stay correct.
<200 lines."""
from src.config.theme import is_dark, zebra_colors

_TAGS = ("zebra0", "zebra1")


def zebra_tree(tree):
    """Alternate zebra0/zebra1 backgrounds over the tree's rows."""
    try:
        even, odd = zebra_colors(is_dark())
        tree.tag_configure("zebra0", background=even)
        tree.tag_configure("zebra1", background=odd)
        for i, iid in enumerate(tree.get_children("")):
            tags = [tg for tg in tree.item(iid, "tags") if tg not in _TAGS]
            tree.item(iid, tags=tuple([_TAGS[i % 2]] + tags))
    except Exception:
        pass


def zebra_listbox(lb):
    """Alternate row backgrounds in a tk.Listbox (a RoundedListbox
    wrapper is unwrapped to its inner Listbox first)."""
    try:
        lb = getattr(lb, "listbox", lb)
        even, odd = zebra_colors(is_dark())
        for i in range(lb.size()):
            lb.itemconfigure(i, background=even if i % 2 == 0 else odd)
    except Exception:
        pass
