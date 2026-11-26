"""Round 48 (owner override 2026-11-23 14:39): the vivid row
palette is EXACTLY the five round-40 colours of gallery shot
137 — no colour added, none substituted — REORDERED so no two
tonally-close colours are ever neighbours. This file SUPERSEDES
tests/test_r47_palette.py (deleted): the round-47 violet and
the saturated round-41/47 set are withdrawn at the owner's word,
an hour after he had approved the violet.

RECOVERY of the five hexes: no hex list survived in the
round-40 gate artifacts, so the colours were pixel-sampled with
PIL from shots 137/138/139 (History-table row bands; identical
values in all three shots):
  sky blue #BAE6FD | lavender #DDD6FE | pink #FBCFE8
  green #BBF7D0 | orange #FED7AA      (Tailwind-200 pastels)

REORDER (brute force over all 12 distinct 5-cycles, colorsys
hues: blue 200.6 | orange 32.1 | lavender 250.5 | green 141.0 |
pink 325.9): the adopted cycle blue -> orange -> lavender ->
green -> pink maximizes the minimum adjacent hue gap:
  gaps incl. the pink -> blue wrap:
  168.5 / 141.6 / 109.5 / 175.1 / 125.3   (minimum 109.5)
The set's two closest colours by hue — blue and lavender,
49.9 degrees apart — are NOT neighbours in this cycle.

Measured bars at pin time (the app's contrast_ratio):
  dark row text #2C241D on the five: 10.98–12.58:1 (>= 4.5)
  selection #7C3AED luminance vs the five: 4.10–4.70:1
  selection hue distance: 61.5 / 130.0 / 121.1 / 63.8 for blue /
  orange / green / pink — and 11.6 for LAVENDER, which therefore
  does NOT meet the round-41 ">= 50 degrees of hue" clause.
  That is recorded, not hidden (see tests/test_r40_vivid_rows.py
  for the waiver pin): lavender's distinctness from the
  selection rests on its 4.10:1 luminance depth + inverted text.
"""
import colorsys

from src.ui.clinical_table_style import contrast_ratio
from src.ui.vivid_rows import (PALETTE, PALETTE_NAMES, TEXT_ON_VIVID,
                               SELECT_BG, SELECT_FG)

EXPECTED = ("#BAE6FD", "#FED7AA", "#DDD6FE", "#BBF7D0", "#FBCFE8")
EXPECTED_NAMES = ("sky blue", "orange", "lavender", "green", "pink")
BLUE = "#BAE6FD"
LAVENDER = "#DDD6FE"


def _hue_deg(hexv):
    r = int(hexv[1:3], 16) / 255; g = int(hexv[3:5], 16) / 255
    b = int(hexv[5:7], 16) / 255
    return colorsys.rgb_to_hsv(r, g, b)[0] * 360.0


def _hue_dist(a, b):
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def test_palette_is_the_recovered_five_in_the_new_order():
    """The exact recovered round-40 palette and names, in the
    reordered rotation; the period is five — nothing added."""
    assert PALETTE == EXPECTED, PALETTE
    assert PALETTE_NAMES == EXPECTED_NAMES, PALETTE_NAMES
    assert len(PALETTE) == 5


def test_adjacent_hue_gaps_at_least_100_incl_wrap():
    """Computed from PALETTE itself: every adjacent pair in the
    cycle — including the wrap from pink back to blue — sits
    >= 100 degrees apart on the colour wheel (measured minimum
    109.5), so no two tonally-close colours ever touch."""
    hues = [_hue_deg(c) for c in PALETTE]
    n = len(hues)
    gaps = [_hue_dist(hues[i], hues[(i + 1) % n]) for i in range(n)]
    assert min(gaps) >= 100.0, gaps


def test_closest_pair_never_adjacent():
    """Blue (200.6) and lavender (250.5) are the palette's
    closest pair by hue (49.9 degrees) — the owner's rule puts
    other colours between them: in the cycle they must never
    sit side by side, in either direction, wrap included."""
    n = len(PALETTE)
    ib, il = PALETTE.index(BLUE), PALETTE.index(LAVENDER)
    assert (ib - il) % n not in (1, n - 1), (ib, il)


def test_restored_colours_measured_bars():
    """Every restored colour meets the standing bars: dark text
    readable on it (>= 4.5:1) and the selection standing off it
    by >= 2:1 luminance with inverted text. (Lavender's hue
    distance to the selection is 11.6 degrees — under the
    round-41 50-degree clause; that single documented exception
    is pinned in test_r40_vivid_rows.py, not waived here.)"""
    for bg in PALETTE:
        assert contrast_ratio(TEXT_ON_VIVID, bg) >= 4.5, (bg,)
        assert contrast_ratio(SELECT_BG, bg) >= 2.0, (bg,)
    assert SELECT_FG == "#FFFFFF" and TEXT_ON_VIVID == "#2C241D"
    assert contrast_ratio(SELECT_FG, SELECT_BG) >= 4.5
