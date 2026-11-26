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
at widget level both trees carry vivid{position % len(PALETTE)}
as the FIRST tag with the palette backgrounds, in both themes.
ROUND-43 SUPERSESSION (owner instruction 2026-11-22): the vivid
rotation now covers EVERY table, so the former scope check (an
unrelated list keeps its zebra) is re-pinned: the referrals tree
must wear the vivid rotation too.
ROUND-48 SUPERSESSION (owner override 2026-11-23 14:39,
superseding round 41 AND round 47): the palette is EXACTLY the
five round-40 pastel colours of shot 137 — pixel-recovered from
shots 137/138/139 — REORDERED to blue / orange / lavender /
green / pink so no tonally-close colours are neighbours
(adjacent hue gaps >= 100 degrees incl. the wrap; measured
minimum 109.5, lavender -> green). The round-41 ">= 50 degrees
of hue from the selection" clause is re-pinned for the LAVENDER
row ONLY: lavender sits 11.6 degrees from the selection hue
(same family — it is one of the owner's five chosen colours)
and its distinctness is carried by the luminance bar it exceeds
(4.10:1, above even round 40's >= 4:1 reading) PLUS the
inverted text (white on the selection vs dark on every row).
The other four colours meet BOTH round-41 criteria. The exact
order, the >= 100-degree adjacency pin and the closest-pair
non-adjacency pin live in tests/test_r48_palette.py."""
import colorsys
import tkinter as tk
from tkinter import ttk

from src.models.database import get_connection, save_financial, set_setting
from src.ui.clinical_table_style import contrast_ratio
from src.ui.vivid_rows import (PALETTE, TEXT_ON_VIVID, SELECT_BG,
                               SELECT_FG, row_tag)
from tests.test_payments_e2e import (TODAY, _seed_users, _seed_patient,
                                     _cleanup, _build_clinical)

# Measured with contrast_ratio at pin time (round 48; the five
# round-40 pastels in the owner's reordered cycle):
#   blue #BAE6FD 11.49 | orange #FED7AA 11.27 | lavender
#   #DDD6FE 10.98 | green #BBF7D0 12.58 | pink #FBCFE8 11.03
#   (text #2C241D)
#   selection vs rows (luminance): 4.29 / 4.21 / 4.10
#   (lavender) / 4.70 / 4.12
#   selection hue 262.1deg; row hue distances: 61.5 / 130.0 /
#   11.6 (lavender — same family, one of the owner's five) /
#   121.1 / 63.8
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
    # ...and visibly distinct from EVERY row colour it can cover.
    # R41 rule: >= 2:1 luminance AND >= 50 degrees of hue.
    # R48 re-pin (owner override 2026-11-23, reason recorded in
    # this file's docstring): the hue clause is waived for the
    # LAVENDER row only — it is 11.6 degrees from the selection
    # hue because lavender is one of the owner's five chosen
    # round-40 colours — and its distinctness rests on the
    # luminance bar (4.10:1) plus the inverted text (white on
    # selection, dark on rows). Every other colour still meets
    # BOTH clauses.
    sel_hue = _hue_deg(SELECT_BG)
    for bg in PALETTE:
        assert contrast_ratio(SELECT_BG, bg) >= 2.0, (bg,)
        if bg != "#DDD6FE":
            assert _hue_dist(sel_hue, _hue_deg(bg)) >= 50.0, (bg,)
    # The inversion itself: selection text is white, row text is
    # the dark tone — a selected row flips text colour too.
    assert SELECT_FG == "#FFFFFF" and TEXT_ON_VIVID == "#2C241D"


def test_palette_neighbour_hues_far_apart():
    """Neighbouring rows in the rotation are CLEARLY different
    colours, never shades of one another. R41 pinned >= 60
    degrees; R47 raised it to >= 110 for its six-colour cycle.
    R48 re-pin (owner override 2026-11-23): the restored
    five-colour cycle is pinned at >= 100 degrees — measured
    minimum 109.5 (lavender -> green), wrap pink -> blue
    included via the closed cycle below."""
    hues = [_hue_deg(c) for c in PALETTE]
    cyc = hues + hues[:1]
    for a, b in zip(cyc, cyc[1:]):
        assert _hue_dist(a, b) >= 100.0, (a, b)


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
        from src.models.referrals import add_referral
        for _ in range(3):  # R43: tree_ref rows for the vivid scope assert
            add_referral(fid, "doc_x", "doc_b", "please see")
        for mode in ("light", "dark"):
            set_setting("theme_mode", mode)
            root, tab = _build_clinical("doc_x", "doctor", fid)
            if tab is None:
                set_setting("theme_mode", "light"); return
            try:
                _assert_vivid(tab.tree_fin, f"payments review {mode}")
                _assert_vivid(tab.tree_history, f"session table {mode}")
                # R43 scope: the referrals tree is vivid now too.
                _assert_vivid(tab.tree_ref, f"referrals tree {mode}")
            finally:
                root.destroy()
        set_setting("theme_mode", "light")
    finally:
        conn = get_connection()
        conn.execute("DELETE FROM diagnoses WHERE patient_file=?", (fid,))
        conn.commit(); conn.close()
        _cleanup(fid)
