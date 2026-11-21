"""Round 34 — teeth render refinement pins (owner feedback on the
round-33 gallery: serrated incisal edges, four named imperfections,
taller teeth). All bars measured on the shipped round-34 assets
(convert_r34_teeth.py: distance-limited tinted barrier + supersampled
premultiplied downscale + top-anchored fit); round-33 values quoted
in comments are the pre-fix measurements they replace. Pure PIL +
stdlib: the gate venv has no numpy/scipy.

Pins:
- serration: the top profile (first alpha>128 pixel per column) of
  every tooth is smooth - max adjacent step <= 3 over the middle of
  the span. Round 33's bitten 43 measured 5 and its shadow-finned
  81 measured 17-18 on this metric; round 34 measures <= 3 on all.
- incisor edges are flat: profile range over the middle 50% <= 4.
- no detached fragments: alpha>128 is a single component per tooth.
- vertical anchor: every tooth's alpha top sits at y <= 2 and all
  52 tops span <= 2 px (round 33 centred them, tops ranged 10-29,
  which is why upper molars sat low in their cells).
- length: permanent mean alpha height >= 78 (round 33: 63.8),
  deciduous mean >= 60 (round 33: 51.7) and at least 10 below the
  permanent mean; canines >= 86, upper centrals >= 88, first
  molars >= 74 - crown:root ratios are the sources' own (uniform
  scaling), only the occupancy of the 48x96 cell grew.
- 14 vs 15: the first premolar is clearly larger - height at
  least +4 and alpha area at least 1.08x the second premolar's
  (round 33 read as near-twins).
- 54's roots are thick: mean alpha width over the root band
  (60-88% of the bbox) >= 18 (round 33 wiry roots: 13.9).
"""
import pathlib

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEETH = ROOT / "assets" / "teeth"
PERM = [11, 12, 13, 14, 15, 16, 17, 18, 21, 22, 23, 24, 25, 26, 27, 28,
        31, 32, 33, 34, 35, 36, 37, 38, 41, 42, 43, 44, 45, 46, 47, 48]
DECID = [51, 52, 53, 54, 55, 61, 62, 63, 64, 65,
         71, 72, 73, 74, 75, 81, 82, 83, 84, 85]
INCISORS = [11, 12, 21, 22, 31, 32, 41, 42, 51, 52, 61, 62, 71, 72, 81, 82]


def _img(n):
    return Image.open(TEETH / f"tooth_{n}.png")


def _alpha_rows(n):
    """Alpha channel as a list of 96 rows of 48 ints."""
    a = _img(n).getchannel("A")
    w, h = a.size
    px = list(a.getdata())
    return [px[y * w:(y + 1) * w] for y in range(h)]


def _profile(n):
    rows = _alpha_rows(n)
    cols = []
    for x in range(48):
        top = next((y for y in range(96) if rows[y][x] > 128), None)
        if top is not None:
            cols.append((x, top))
    return cols


def _bbox(n):
    return _img(n).getchannel("A").getbbox()


def _height(n):
    bb = _bbox(n)
    return bb[3] - bb[1]


def _area(n):
    return sum(1 for v in _img(n).getchannel("A").getdata() if v > 128)


def _components(n):
    rows = _alpha_rows(n)
    seen = [[False] * 48 for _ in range(96)]
    sizes = []
    for y in range(96):
        for x in range(48):
            if rows[y][x] > 128 and not seen[y][x]:
                stack, size = [(x, y)], 0
                seen[y][x] = True
                while stack:
                    cx, cy = stack.pop()
                    size += 1
                    for nx, ny in ((cx - 1, cy), (cx + 1, cy),
                                   (cx, cy - 1), (cx, cy + 1)):
                        if (0 <= nx < 48 and 0 <= ny < 96
                                and not seen[ny][nx]
                                and rows[ny][nx] > 128):
                            seen[ny][nx] = True
                            stack.append((nx, ny))
                sizes.append(size)
    return [s for s in sizes if s >= 8]


def test_top_profile_smooth_no_serration():
    for n in PERM + DECID:
        cols = _profile(n)
        span = cols[-1][0] - cols[0][0] + 1
        trim = max(2, int(0.12 * span))
        mid = [y for _, y in cols[trim: len(cols) - trim]]
        steps = [abs(mid[i + 1] - mid[i]) for i in range(len(mid) - 1)]
        assert max(steps) <= 3, f"{n}: top-profile step {max(steps)}"


def test_incisor_edges_flat():
    for n in INCISORS:
        cols = _profile(n)
        q = len(cols) // 4
        mid = [y for _, y in cols[q: len(cols) - q]]
        assert max(mid) - min(mid) <= 4, \
            f"{n}: incisal edge range {max(mid) - min(mid)}"


def test_single_component_no_detached_fragments():
    for n in PERM + DECID:
        big = _components(n)
        assert len(big) == 1, f"{n}: {len(big)} alpha components"


def test_vertical_anchor_consistent():
    tops = [_bbox(n)[1] for n in PERM + DECID]
    assert max(tops) <= 2, f"anchor tops: {sorted(set(tops))}"
    assert max(tops) - min(tops) <= 2, f"anchor spread: {tops}"


def test_teeth_taller_than_round33():
    perm_mean = sum(_height(n) for n in PERM) / len(PERM)
    dec_mean = sum(_height(n) for n in DECID) / len(DECID)
    assert perm_mean >= 78, f"permanent mean height {perm_mean:.1f}"
    assert dec_mean >= 60, f"deciduous mean height {dec_mean:.1f}"
    assert dec_mean <= perm_mean - 10
    for n in (13, 23, 33, 43):
        assert _height(n) >= 86, f"canine {n}: {_height(n)}"
    for n in (11, 21):
        assert _height(n) >= 88, f"central {n}: {_height(n)}"
    for n in (16, 26, 36, 46):
        assert _height(n) >= 74, f"first molar {n}: {_height(n)}"


def test_14_clearly_larger_than_15():
    assert _height(14) >= _height(15) + 4, \
        f"heights 14={_height(14)} 15={_height(15)}"
    assert _area(14) >= 1.08 * _area(15), \
        f"areas 14={_area(14)} 15={_area(15)}"


def test_54_roots_thickened():
    rows = _alpha_rows(54)
    _, y0, _, y1 = _bbox(54)
    band = [sum(1 for v in rows[y] if v > 128)
            for y in range(y0 + int(0.60 * (y1 - y0)),
                           y0 + int(0.88 * (y1 - y0)))]
    mean_w = sum(band) / len(band)
    assert mean_w >= 18, f"54 root-band mean width {mean_w:.1f}"
