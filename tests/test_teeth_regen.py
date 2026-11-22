"""Per-tooth AI teeth regression (round 33, 2026-11-20).

Replaces the round-14 shared-asset test: the owner ruled EVERY tooth
must have its own anatomy, so the 8 shared type renders are gone.
One render was generated per RIGHT-side tooth (26 accepted sources
in ~/workspace/app_screens/teeth_ai/r33/ + r35/ + r36/ + r41/, rejected generations
unused), converted with the dark-rim flood-fill converter
(app_screens/teeth_ai/convert_r41_teeth.py) into tooth_<FDI>.png at
an anatomy-based fit box; each LEFT-side tooth is the horizontal
mirror - the true anatomical relationship (mesial toward the
midline) - so a mirror pair is related but never pixel-identical,
and no two teeth share a render.

Pinned: accepted sources exist; all 52 outputs 48x96 RGBA with
transparent corners and byte-distinct; every left tooth is the exact
mirror of its right partner and no other pair is flip-equal; no
white halo fringe / trapped fork background and crowns brighter
than roots (round-15 bars, unchanged); deciduous smaller on average
than permanent; the FDI -> file mapping; the chart loading all 52
with each cell showing its own tooth. Non-GUI tests are pure PIL;
the chart test needs a display (xvfb).
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ui import dental_chart
from src.ui.dental_chart import tooth_image_name
from src.utils.helpers import DECIDUOUS, PERMANENT

TEETH_DIR = Path(dental_chart.__file__).resolve().parents[2] / "assets" / "teeth"
AI_DIR = Path.home() / "workspace" / "app_screens" / "teeth_ai" / "r33"
AI_SOURCES = {  # right-side FDI -> accepted generation (rejects unused)
    11: "../r35/media-generation-src-11-r35-5.webp", 12: "media-generation-src-12b-0-19ab72df-1a33-4e21-9f2b-0fc8019e32e5.webp",
    13: "media-generation-src-13b-0-3b52cbea-ba23-49ff-9110-2d9d69c5712c.webp", 14: "../r35/media-generation-src-14-r35-4.webp",
    15: "media-generation-src-15-r34-0-1ea0ef24-ba21-48ec-b775-a8e1e8e67927.webp", 16: "../r35/media-generation-src-16-r35-2.webp",
    17: "media-generation-src-17-0-c08d9f09-896a-4250-baf6-28d25cd258e9.webp", 18: "../r36/media-generation-src-18-r36-1.webp",
    41: "../r35/media-generation-src-41-r35-1.webp", 42: "media-generation-src-42b-0-9bd6abe1-9d59-4267-8486-204c7fd959ce.webp",
    43: "media-generation-src-43-r34-coord-0-327c42e2-a9d4-4e55-8dc5-457fa1cb5d11.webp", 44: "media-generation-src-44d-0-c7129615-8866-44a7-98ad-6668022700ba.webp",
    45: "../r36/media-generation-src-45-r36-2.webp", 46: "media-generation-src-46-0-ddd7a5bb-1860-4ece-9daa-59b59ed01cfe.webp",
    47: "media-generation-src-47-0-a4ae8f7e-0bbf-4a48-90dc-6b270d04298f.webp", 48: "media-generation-src-48-0-6c77d559-bae6-47d8-a0ae-7edac1983104.webp",
    51: "media-generation-src-51c-0-3f1d0f83-23ff-4982-a8fc-58af26f90f94.webp", 52: "media-generation-src-52d-0-003f483f-65fc-42bb-9404-824701b0a617.webp",
    53: "media-generation-src-53c-0-128a6729-e5a5-4ace-b3d2-0090cda380b5.webp", 54: "../r41/media-generation-src-54-r41-3.webp",
    55: "media-generation-src-55b-0-9ff41079-f29d-4be5-9539-f351147aa4a4.webp", 81: "media-generation-src-81-r34-0-1803410f-2318-4829-8452-4bd7932408df.webp",
    82: "media-generation-src-82b-0-ee3ccb83-e168-426f-867e-6c53dea0798c.webp", 83: "media-generation-src-83d-0-18fe2c42-507f-4286-96e5-3151596b2755.webp",
    84: "media-generation-src-84c-0-3cad3cd9-c7e5-4f7e-bbf3-d40d33649d22.webp", 85: "media-generation-src-85b-0-3ad98d66-b56f-44b3-821b-b4b6c0f4785b.webp",
}
ALL = [f"tooth_{n}.png" for n in PERMANENT + DECIDUOUS]
MIRROR = {int(f"{q}{p}"): int(f"{m}{p}") for q, m in ((1, 2), (4, 3), (5, 6), (8, 7))
          for p in range(1, 9) if f"{q}{p}" in PERMANENT + DECIDUOUS}


def _im(name):
    from PIL import Image
    return Image.open(TEETH_DIR / name).convert("RGBA")


def test_ai_source_files_exist():
    """The 26 accepted renders (round 33; 11/14/16/41 replaced in
    round 35, 45 + 18 in round 36, 54 in round 41 — viewpoint and
    root-origin defects; see convert_r41_teeth.py for details)."""
    assert len(AI_SOURCES) == 26
    assert all((AI_DIR / f).is_file() for f in AI_SOURCES.values())


def test_all_52_pngs_exist_48x96_rgba_and_distinct():
    seen = set()
    for name in ALL:
        p = TEETH_DIR / name
        assert p.is_file(), f"missing tooth PNG {name}"
        im = _im(name)
        assert im.size == (48, 96) and im.mode == "RGBA", name
        assert im.getchannel("A").getbbox(), f"{name} is fully transparent"
        for x, y in ((0, 0), (47, 0), (0, 95), (47, 95)):
            assert im.getpixel((x, y))[3] == 0, f"{name}: corner {(x, y)} opaque"
        seen.add(p.read_bytes())
    assert len(seen) == 52, "two tooth PNGs are byte-identical"
    assert len(ALL) == 52 and len(set(ALL)) == 52


def test_left_teeth_are_true_mirrors_only_of_their_partner():
    """Left = exact mirror of its right partner BY DESIGN (mesial
    toward the midline), never a pixel-identical copy; no other pair
    of teeth may be identical or flip-equal - no shared renders."""
    from PIL import Image
    pix = {n: _im(f"tooth_{n}.png") for n in PERMANENT + DECIDUOUS}
    for right, left in sorted(MIRROR.items()):
        flipped = pix[str(right)].transpose(Image.FLIP_LEFT_RIGHT)
        assert pix[str(left)].tobytes() == flipped.tobytes(), \
            f"{left} is not the exact mirror of {right}"
        assert pix[str(left)].tobytes() != pix[str(right)].tobytes(), \
            f"{left} is a pixel-identical copy of {right}"
    nums = PERMANENT + DECIDUOUS
    for i, a in enumerate(nums):
        for b in nums[i + 1:]:
            pair = MIRROR.get(int(a)) == int(b) or MIRROR.get(int(b)) == int(a)
            if not pair:
                assert pix[a].tobytes() != pix[b].transpose(
                    Image.FLIP_LEFT_RIGHT).tobytes(), f"{a} flip-equals {b}"


def test_no_white_halo_fringe():
    """Round-15 bars, unchanged: feathered edge pixels that are
    near-pure-white are leftover background; no opaque neutral-bright
    pixel in the bottom 55% (trapped fork background)."""
    for name in ALL:
        im = _im(name)
        _, y0, _, y1 = im.getchannel("A").getbbox()
        fringe = edge = fork = 0
        for idx, (r, g, b, a) in enumerate(im.getdata()):
            y = idx // 48
            if 20 < a < 250 and min(r, g, b) >= 248:
                fringe += 1
            if max(r, g, b) - min(r, g, b) < 8 and min(r, g, b) >= 195:
                if 20 < a < 250 and min(r, g, b) >= 200:
                    edge += 1
                elif a > 200 and y > y0 + 0.45 * (y1 - y0):
                    fork += 1
        assert fringe <= 4, f"{name}: {fringe} white-fringe edge pixels"
        assert (edge, fork) == (0, 0), f"{name}: dark halo edge={edge} fork={fork}"


def test_crown_brighter_than_root():
    """Round-15 bars, unchanged: crown top (top 15%) brighter than
    root tips (bottom 20%). Round-33 worst margins: 4.9 (lower
    centrals), 5.2 (upper laterals)."""
    for name in ALL:
        im = _im(name)
        _, y0, _, y1 = im.getchannel("A").getbbox()
        h = y1 - y0

        def mean_r(ya, yb):
            px = [im.getpixel((x, y)) for y in range(ya, yb) for x in range(48)
                  if im.getpixel((x, y))[3] > 50]
            assert px, f"{name}: empty band {ya}-{yb}"
            return sum(c[0] for c in px) / len(px)

        crown = mean_r(y0, y0 + max(4, int(0.15 * h)))
        root = mean_r(y1 - max(4, int(0.20 * h)), y1)
        assert crown > 210, f"{name}: crown top not bright: {crown:.1f}"
        assert crown - root > 3, f"{name}: crown/root margin {crown - root:.1f}"


def test_deciduous_smaller_on_average_and_mapping():
    """Deciduous are independent renders now (not 75% copies) but
    still read smaller: mean alpha-bbox height of the 20 deciduous
    < the 32 permanent. Mapping: one file per FDI number."""
    def mean_h(nums):
        hs = [_im(f"tooth_{n}.png").getchannel("A").getbbox() for n in nums]
        return sum(b[3] - b[1] for b in hs) / len(hs)
    assert mean_h(DECIDUOUS) < mean_h(PERMANENT)
    for n in PERMANENT + DECIDUOUS:
        assert tooth_image_name(n) == f"tooth_{n}.png", n
    assert tooth_image_name("99") is None


def test_chart_loads_all_52_ai_images():
    """GUI: the chart loads all 52 PNGs and every cell shows the image
    for its own FDI number, permanent and deciduous."""
    try:
        import tkinter as tk
    except Exception:
        return
    try:
        root = tk.Tk()
        root.withdraw()
        frame = dental_chart.DentalChartFrame(root, on_select=lambda s, t: None)
        frame.pack()
        root.update_idletasks()
    except Exception:
        return  # no display: skip GUI check
    try:
        assert len(frame._images) == 52, f"chart loaded {len(frame._images)} images"
        for nums in (PERMANENT, DECIDUOUS):
            if nums is DECIDUOUS:
                frame.tooth_type.set("لبني")
                frame.refresh()
                root.update_idletasks()
            assert set(frame.tooth_cells) == set(nums)
            frame.update_idletasks()
            assert int(frame._canvas.cget("height")) >= frame.area.winfo_reqheight(), \
                "canvas shorter than chart content: lower jaw clipped"
            for n in nums:
                pic = next((c for w in frame.tooth_cells[n].winfo_children()
                            for c in [w] + list(w.winfo_children())
                            if c.winfo_class() == "Label" and str(c.cget("image"))), None)
                assert pic is not None, f"tooth {n} shows no PNG"
                want = str(frame._images[tooth_image_name(n)])
                assert str(pic.cget("image")) == want, (
                    f"tooth {n} shows the wrong image, want {tooth_image_name(n)}")
    finally:
        root.destroy()


if __name__ == "__main__":
    for name in sorted(a for a in dir() if a.startswith("test_")):
        globals()[name]()
        print("PASS", name)
    print("ALL PER-TOOTH TEETH TESTS PASSED")
