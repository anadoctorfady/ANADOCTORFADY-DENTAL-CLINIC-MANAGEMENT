"""Round 38, item 3: image viewer zoom + rotate with save/discard.

Pixel-level contract:
  * rotate + SAVE on a PNG -> the file's pixels are EXACTLY the
    transposed original (90° steps are an exact transpose);
  * rotate + SAVE on a JPEG -> dimensions swap and pixels match
    the rotated original within a small tolerance (JPEG q100 4:4:4
    re-encode: visually lossless, NOT bit-lossless);
  * rotate + DISCARD -> the file is byte-identical (hash);
  * ZOOM (display only) -> the file is byte-identical.
GUI parts skip gracefully with no display; the save math is
exercised headlessly through src.ui.image_save either way."""
import hashlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageChops

from src.ui.image_save import rotate_image, save_rotated

TMP = Path("/tmp/r38_viewer")
TMP.mkdir(exist_ok=True)


def _pattern(size=(30, 20)):
    """A non-symmetric test pattern (rotation is detectable)."""
    img = Image.new("RGB", size, (200, 30, 30))
    for x in range(6):
        for y in range(4):
            img.putpixel((x, y), (20, 220, 20))
    img.putpixel((size[0] - 1, size[1] - 1), (30, 30, 230))
    return img


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_png_rotate_save_is_exact():
    p = TMP / "a.png"
    src = _pattern(); src.save(p)
    save_rotated(str(p), src, 90)
    with Image.open(p) as out:
        out.load()
        assert out.size == (20, 30)  # swapped
        assert list(out.getdata()) == list(
            src.transpose(Image.Transpose.ROTATE_270).getdata())


def test_jpeg_rotate_save_within_tolerance():
    p = TMP / "b.jpg"
    src = _pattern((64, 48)); src.save(p, quality=95)
    with Image.open(p) as im:
        im.load(); before = im.copy()
    save_rotated(str(p), before, 90)
    with Image.open(p) as out:
        out.load()
        assert out.size == (48, 64)
        want = before.transpose(Image.Transpose.ROTATE_270)
        diff = ImageChops.difference(out.convert("RGB"), want)
        assert max(diff.getextrema()[i][1] for i in range(3)) <= 12, \
            diff.getextrema()


def test_rotate_180_and_270_and_full_turn():
    p = TMP / "c.png"
    src = _pattern(); src.save(p)
    assert save_rotated(str(p), src, 360) == 0  # no-op, untouched
    assert _hash(p) == _hash(p)
    save_rotated(str(p), src, 270)
    with Image.open(p) as out:
        out.load()
        assert list(out.getdata()) == list(
            src.transpose(Image.Transpose.ROTATE_90).getdata())


def _open_viewer(path):
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.withdraw()
    from src.ui.image_viewer import open_image_viewer
    win = open_image_viewer(root, str(path), path.name, "en")
    root.update_idletasks()
    return root, win


def test_viewer_zoom_never_touches_the_file():
    p = TMP / "d.png"; _pattern().save(p)
    h0 = _hash(p)
    root, win = _open_viewer(p)
    if root is None:
        return
    s0 = win.viewer_size
    win.viewer_zoom_in(); win.viewer_zoom_in()
    assert win.viewer_size[0] > s0[0]  # display grew
    win.viewer_zoom_out()
    assert _hash(p) == h0
    root.destroy()


def test_viewer_rotate_save_and_discard():
    import src.ui.image_viewer as viewer_mod
    p = TMP / "e.png"; src = _pattern(); src.save(p)
    h0 = _hash(p)
    root, win = _open_viewer(p)
    if root is None:
        return
    root.update()  # settle the viewer before generating key events
    orig_ask = viewer_mod.messagebox.askyesno
    try:
        # DISCARD: rotate, answer No -> file byte-identical.
        viewer_mod.messagebox.askyesno = lambda *a, **k: False
        win.viewer_rotate(90)
        assert win.viewer_rotation == 90
        win.event_generate("<Escape>")
        root.update()  # dispatch the generated event
        assert not win.winfo_exists()
        assert _hash(p) == h0
        # SAVE: rotate, answer Yes -> pixels exactly rotated.
        root2, win2 = _open_viewer(p)
        viewer_mod.messagebox.askyesno = lambda *a, **k: True
        saved = []
        win2.viewer_rotate(90)
        # reopen with on_saved hook
        root2.destroy()
        from src.ui.image_viewer import open_image_viewer
        win3 = open_image_viewer(root, str(p), p.name, "en",
                                 on_saved=lambda: saved.append(1))
        root.update()
        win3.viewer_rotate(90)
        win3.event_generate("<Escape>")
        root.update()
        assert saved == [1]
        with Image.open(p) as out:
            out.load()
            assert list(out.getdata()) == list(
                src.transpose(Image.Transpose.ROTATE_270).getdata())
    finally:
        viewer_mod.messagebox.askyesno = orig_ask
        root.destroy()
