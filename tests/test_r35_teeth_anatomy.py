"""Round 35 — teeth anatomy corrections, second owner feedback pass
(owner reviewed the round-34 chart as a dentist). Four items; this
file pins what is measurable at 48x96 and says plainly what is not.

1. Tooth 11 (and mirror 21): the incisal edge read as WORN. The old
   source's edge was wavy with an abraded translucent band; the
   round-35 source has a clean straight unworn edge, mesial incisal
   angle sharp (~90deg), distal angle rounded. Pinned below on the
   top profile (file orientation: crown at top): the edge plateau
   is flat (middle-50% range 0, bar <= 1; round-34 asset measured
   range 1 with a 7-column distal slope from its crown bulge) and
   the corner descent runs show the asymmetry - mesial reaches the
   edge within 2 columns (sharp), distal takes at least one column
   longer (rounded). Measured on the shipped assets: 11/21 plateau
   range 0, mesial run 2, distal run 3. Laterals 12/22 and lower
   laterals 42/32 pin the same asymmetry DIRECTION (distal run >
   mesial run; measured 9>2 and 5>2). Lower centrals 31/41 pin edge
   FLATNESS only (range <= 1, measured 1): at 48x96 their mesial/
   distal angle difference is sub-pixel (runs 3 vs 4, within noise),
   so their angles were verified visually on the source instead.
   The other anterior teeth (13/23/33/43 canines, deciduous
   anteriors) were audited visually on assets + sources: tips
   pointed and intact, edges unworn - no regeneration needed.
2. Tooth 26/16 palatal root: from the buccal view its origin must
   stay hidden behind the root trunk, the root peeking only through
   the buccal fork - the pattern 27/17 already had. This is an
   outline/shading feature of the render, NOT a silhouette property
   (the palatal silhouette is continuous with the trunk either
   way), so at 48x96 it is not honestly machine-checkable. It is
   pinned by provenance (test_teeth_regen points tooth 16 at the
   round-35 source, whose palatal origin is hidden like 17's) and
   verified on the gallery acceptance crops (16 vs 17, 26 vs 27).
   Tooth 18/28 audited: fused/convergent roots, consistent.
3. Teeth 31/41 BLUE HALO: the round-33 source for 41 carried a
   baked-in drop shadow hugging the root; conversion kept it as a
   neutral grey skirt, which reads blue against the warm chart
   background #F6F1E9. Round-34 checks measured alpha fringe and
   dark rim, never colour cast - the gap this item closes. The
   round-35 source is verified shadow-free. Pinned below for ALL
   52 teeth: the semi-transparent edge band (20<alpha<250),
   composited over the chart background, must stay warm - its
   blue excess (mean of (B-Bbg) - ((R-Rbg)+(G-Gbg))/2 over band
   pixels) must be <= -3.5. Measured: the round-34 halo pair
   scored -2.91 (would FAIL this bar), the worst healthy tooth
   (34/44, loose detached shadow only) scores -4.36, and the
   fixed 31/41 score -16.06 (also pinned individually at <= -10).
4. Tooth 14/24 BUCCAL view: the old render was a mesial/side view.
   The round-35 source is a true buccal view in 15's viewpoint
   family (provenance-pinned in test_teeth_regen; size dominance
   over 15 still pinned by test_r34_teeth_refine; the viewpoint
   itself verified on the 14 vs 15 gallery crop).

Pure PIL + stdlib, like the other teeth tests.
"""
import pathlib

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEETH = ROOT / "assets" / "teeth"
PERM = [11, 12, 13, 14, 15, 16, 17, 18, 21, 22, 23, 24, 25, 26, 27, 28,
        31, 32, 33, 34, 35, 36, 37, 38, 41, 42, 43, 44, 45, 46, 47, 48]
DECID = [51, 52, 53, 54, 55, 61, 62, 63, 64, 65,
         71, 72, 73, 74, 75, 81, 82, 83, 84, 85]
BG = (0xF6, 0xF1, 0xE9)  # chart background (light theme th["bg"])


def _img(n, flip=False):
    im = Image.open(TEETH / f"tooth_{n}.png").convert("RGBA")
    return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im


def _blue_excess(n):
    """Mean blue excess of the semi-transparent edge band over the
    chart background; warm enamel bands are strongly negative."""
    tot, cnt = 0.0, 0
    for r, g, b, a in _img(n).getdata():
        if 20 < a < 250:
            af = a / 255.0
            cr = r * af + BG[0] * (1 - af)
            cg = g * af + BG[1] * (1 - af)
            cb = b * af + BG[2] * (1 - af)
            tot += (cb - BG[2]) - ((cr - BG[0]) + (cg - BG[1])) / 2
            cnt += 1
    assert cnt > 50, f"{n}: edge band too small ({cnt}px)"
    return tot / cnt


def _profile(n, flip=False):
    """Top profile (first alpha>128 row per column), crown at top.
    flip=True normalises a left-side tooth so mesial is image-right,
    the same convention as its right-side partner."""
    a = _img(n, flip).getchannel("A")
    px = list(a.getdata())
    cols = []
    for x in range(48):
        top = next((y for y in range(96) if px[y * 48 + x] > 128), None)
        if top is not None:
            cols.append(top)
    return cols


def _edge_runs(cols):
    """(plateau range over middle 50%, distal run, mesial run) for a
    right-side-oriented incisor: a run counts the columns from that
    side until the profile first reaches plateau+1 - a sharp corner
    reaches the edge in few columns, a rounded corner takes more."""
    mid = cols[len(cols) // 4: len(cols) - len(cols) // 4]
    plateau = min(mid)

    def run(seq):
        for i, t in enumerate(seq):
            if t <= plateau + 1:
                return i
        return len(seq)

    return max(mid) - min(mid), run(cols), run(list(reversed(cols)))


def test_no_colour_cast_halo_any_tooth():
    worst = []
    for n in PERM + DECID:
        v = _blue_excess(n)
        worst.append((v, n))
        assert v <= -3.5, f"{n}: edge-band blue excess {v:.2f} (halo)"
    worst.sort(reverse=True)
    assert worst[0][0] <= -3.5, f"worst tooth {worst[0]}"


def test_31_41_halo_eliminated():
    for n in (31, 41):
        v = _blue_excess(n)
        assert v <= -10.0, f"{n}: blue excess {v:.2f} (was -2.91 in r34)"


def test_upper_central_edge_flat_mesial_sharp_distal_rounded():
    for n, flip in ((11, False), (21, True)):
        rng, distal, mesial = _edge_runs(_profile(n, flip))
        assert rng <= 1, f"{n}: incisal edge plateau range {rng}"
        assert mesial <= 2, f"{n}: mesial corner run {mesial} (not sharp)"
        assert distal >= mesial + 1, \
            f"{n}: distal run {distal} !> mesial run {mesial} (not rounded)"


def test_incisor_asymmetry_direction():
    for n, flip in ((12, False), (22, True), (42, False), (32, True)):
        _, distal, mesial = _edge_runs(_profile(n, flip))
        assert distal > mesial, \
            f"{n}: distal run {distal} !> mesial run {mesial}"


def test_lower_central_edges_flat_unworn():
    for n, flip in ((41, False), (31, True)):
        rng, _, _ = _edge_runs(_profile(n, flip))
        assert rng <= 1, f"{n}: incisal edge plateau range {rng}"
