"""Row striping for multi-row tables/lists.

Round 21 gave every multi-row Treeview/list two alternating
zebra backgrounds; round 40/41 added the vivid 5-colour rotation
on two money lists. Round 43 (owner, explicit instruction
2026-11-22): EVERY table's rows must rotate vivid colours, each
row different from the row before and after it. These two helpers
therefore DELEGATE to src.ui.vivid_rows, so every existing call
site (all at the END of a fill routine) picks up the rotation
with no per-site change.

Meaning FOREGROUNDS are preserved: ttk tag precedence follows
tag CREATION order (first-configured tag wins a conflicting
option -- probed on DISPLAY:98, 2026-11-22), and every meaning
tag in the app (patient name colours, the red "debt" tag,
appointment attendance statuses) is configured BEFORE the first
striping call on its tree; the vivid tags set the background and
a dark foreground that those earlier tags still override.
<200 lines."""
from src.ui.vivid_rows import vivid_listbox, vivid_tree


def zebra_tree(tree):
    """Round 43: vivid rotation over the tree's rows (was zebra)."""
    vivid_tree(tree)


def zebra_listbox(lb):
    """Round 43: vivid rotation in a tk.Listbox (a RoundedListbox
    wrapper is unwrapped to its inner Listbox first)."""
    vivid_listbox(lb)
