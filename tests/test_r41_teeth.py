"""Round 41, item 1: tooth 54 regenerated — straight buccal
view, palatal root origin hidden behind the root trunk (the
defect class fixed for 16/26 in round 35; the owner reported
54/64 from live use of the round-40 build).

The measurable silhouette signature: in DISPLAYED orientation
(upper jaw flipped at load, roots pointing up) the OLD 54 asset
showed THREE separate root-tip clusters along the tip band —
the two buccal roots plus the exposed palatal root standing
between them. The regenerated asset shows exactly TWO clusters
(the buccal pair); the palatal root is hidden behind the trunk.
64 is 54's exact mirror (pinned in test_teeth_flip) and must
show the same count. Root thickness stays under the round-34
bar (test_r34_teeth_refine.test_54_roots_thickened, unchanged):
the first TWO regenerated candidates were REJECTED for failing
it (band widths 15.9 and 17.5, both < 18 — right silhouette,
roots too slender) and the accepted source is the third
candidate, with roots and trunk thickened ~15%."""
from pathlib import Path

from PIL import Image

ASSETS = Path(__file__).resolve().parents[1] / "assets" / "teeth"


def _tip_clusters(fdi):
    im = Image.open(ASSETS / f"tooth_{fdi}.png").convert("RGBA")
    im = im.transpose(Image.FLIP_TOP_BOTTOM)  # displayed orientation
    a = im.getchannel("A")
    w, h = im.size
    px = a.load()
    rows = [y for y in range(h)
            if any(px[x, y] > 128 for x in range(w))]
    y0, y1 = min(rows), max(rows)
    band_h = max(2, int((y1 - y0 + 1) * 0.12))
    cols = [any(px[x, y] > 128 for y in range(y0, y0 + band_h))
            for x in range(w)]
    clusters, run = 0, False
    for c in cols:
        if c and not run:
            clusters += 1; run = True
        elif not c:
            run = False
    return clusters


def test_54_two_buccal_root_tips_only():
    assert _tip_clusters(54) == 2, _tip_clusters(54)
    assert _tip_clusters(64) == 2, _tip_clusters(64)
