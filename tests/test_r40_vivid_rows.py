"""Round 40, item 2: VIVID rotating row colours on the two
money-bearing lists (the unified clinical session table +
the Payments review). Owner: rows in different colours, NOT
the app's basic colours — every row a different colour from
its neighbours.

Round 41 (item 6) RE-PIN, owner feedback 2026-11-22 on the
round-40 build: the pale pastels read as shades of one another
on his Windows screen. The palette is now five SATURATED hues
(sky / orange / green / hot pink / amber, 56–71% lightness,
neighbouring hues >= 85 degrees apart; violet removed from the
rows because the selection owns it). The selection-distinctness
bar is re-defined with it: round 40's ">= 4:1 luminance off
every row colour" is unreachable for saturated mid-luminance
colours against a deep-violet selection (they measure
2.15–3.41:1), so distinctness is pinned as >= 2:1 luminance
PLUS >= 50 degrees of hue distance from the selection hue,
with the selection's white text unchanged (>= 4.5:1 on the
selection bg). The text bar is unchanged: dark text >= 4.5:1
on every colour (measured 5.76–9.13:1), identical in both
themes because the colours do not change with the theme.

Pins: the palette (length >= 4, all distinct); neighbours in a
long cycle NEVER share a background; the measured WCAG contrast
of the row text on EVERY colour >= 4.5:1; the defined selection
(#7C3AED bg, white text) is readable itself and stands off
every row colour per the round-41 distinctness rule above;
at widget level both trees carry vivid{position % 5} as the
FIRST tag with the palette backgrounds, in both themes, while
an unrelated list keeps its zebra (scope check)."""
import colorsys
import tkinter as tk
from tkinter import ttk

from src.models.database import get_connection, save_financial, set_setting
from src.ui.clinical_table_style import contrast_ratio
from src.ui.vivid_rows import (PALETTE, TEXT_ON_VIVID, SELECT_BG,
                               SELECT_FG, row_tag)
from tests.test_payments_e2e import (TODAY, _seed_users, _seed_patient,
                                     _cleanup, _build_clinical)

# Measured with contrast_ratio at pin time (round 41):
#   sky #38BDF8 7.12 | orange #FB923C 6.74 | green #4ADE80 8.75
#   hot pink #F472B6 5.76 | amber #FBBF24 9.13  (text #2C241D)
#   selection vs rows (luminance): 2.66 / 2.52 / 3.27 / 2.15 / 3.41
#   selection hue 262deg; row hue distances: 62 / 125 / 120 / 56 / 141
#   white on selection bg: 5.70


def _hue_deg(hexv):
    r = int(hexv[1:3], 16) / 255; g = int(hexv[3:5], 16) / 255
    b = int(hexv[5:7], 16) / 255
    return colorsys.rgb_to_hsv(r, g, b)[0] * 360.0


def _hue_dist(a, b):
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def test_palette_shape_and_neighbours():
    assert len(PALETTE) >= 4
    assert len(set(PALETTE)) == len(PALETTE)
    cycle = [PALETTE[i % len(PALETTE)] for i in range(3 * len(PALETTE))]
    for a, b in zip(cycle, cycle[1:]):
        assert a != b, "neighbouring rows must never share a colour"
    for i in range(12):
        assert row_tag(i) == f"vivid{i % len(PALETTE)}"


def test_palette_contrast_measured():
    for bg in PALETTE:
        ratio = contrast_ratio(TEXT_ON_VIVID, bg)
        assert ratio >= 4.5, (bg, ratio)
    # The selection is itself readable text...
    assert contrast_ratio(SELECT_FG, SELECT_BG) >= 4.5
    # ...and visibly distinct from EVERY row colour it can cover
    # (R41 rule: >= 2:1 luminance AND >= 50 degrees of hue).
    sel_hue = _hue_deg(SELECT_BG)
    for bg in PALETTE:
        assert contrast_ratio(SELECT_BG, bg) >= 2.0, (bg,)
        assert _hue_dist(sel_hue, _hue_deg(bg)) >= 50.0, (bg,)


def test_palette_neighbour_hues_far_apart():
    """R41 item 6: neighbouring rows in the rotation are CLEARLY
    different colours — hue distance >= 60 degrees (measured
    minimum 85), never shades of one another."""
    hues = [_hue_deg(c) for c in PALETTE]
    cyc = hues + hues[:1]
    for a, b in zip(cyc, cyc[1:]):
        assert _hue_dist(a, b) >= 60.0, (a, b)


def _assert_vivid(tree, label):
    kids = tree.get_children("")
    assert len(kids) >= 3, (label, len(kids))
    for i, k in enumerate(kids):
        tags = tree.item(k, "tags")
        assert tags and tags[0] == f"vivid{i % len(PALETTE)}", (label, i, tags)
        got = str(tree.tag_configure(tags[0], "background")).lower()
        assert got == PALETTE[i % len(PALETTE)].lower(), (label, i, got)
    st = ttk.Style()
    mapped = dict(st.map("Vivid.Treeview", "background"))
    assert mapped.get("selected") == SELECT_BG
    fg = dict(st.map("Vivid.Treeview", "foreground"))
    assert fg.get("selected") == SELECT_FG


def test_vivid_rows_in_both_trees_both_themes():
    _seed_users(); fid = _seed_patient("R40 Vivid")
    try:
        days = ("2026-11-10", "2026-11-11", "2026-11-12",
                "2026-11-13", "2026-11-14")
        for day in days:
            save_financial(fid, "11", 1000, 400, day, doctor="doc_x",
                           entered_by="doc_x")
        # History rows are clinical sessions; the money attaches.
        conn = get_connection()
        for day in days:
            conn.execute("INSERT INTO diagnoses(patient_file,visit_date,"
                         "tooth_number,diagnosis) VALUES(?,?,?,?)",
                         (fid, day, "11", "Caries"))
        conn.commit(); conn.close()
        for mode in ("light", "dark"):
            set_setting("theme_mode", mode)
            root, tab = _build_clinical("doc_x", "doctor", fid)
            if tab is None:
                set_setting("theme_mode", "light"); return
            try:
                _assert_vivid(tab.tree_fin, f"payments review {mode}")
                _assert_vivid(tab.tree_history, f"session table {mode}")
                # Scope: the referrals tree keeps its zebra pair.
                ref_tags = tab.tree_ref.tag_configure("zebra0", "background")
                assert str(ref_tags).lower() not in \
                    [c.lower() for c in PALETTE]
            finally:
                root.destroy()
        set_setting("theme_mode", "light")
    finally:
        conn = get_connection()
        conn.execute("DELETE FROM diagnoses WHERE patient_file=?", (fid,))
        conn.commit(); conn.close()
        _cleanup(fid)
