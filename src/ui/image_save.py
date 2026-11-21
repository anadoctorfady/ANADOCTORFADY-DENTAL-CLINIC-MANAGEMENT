"""Rotate-and-save for the image viewer (Round 38, item 3).

Display zooming NEVER touches the file. Rotation is the only
change a user can save, and it is saved exactly: 90° steps are a
pixel transpose (PIL Transpose), so no resampling ever happens.

Write-back by format (same filename, same format):
  PNG / BMP / TIFF / GIF — the format itself is lossless.
  JPEG — re-encoded at quality=100 with 4:4:4 subsampling
    (subsampling=0). This is VISUALLY lossless, not bit-lossless:
    JPEG is a lossy format, so the decoded pixels can differ from
    the original by tiny DCT rounding even at q100 — stated
    honestly; the rotation itself adds no further loss.
  WEBP — saved with lossless=True.
  Anything else — saved in its own format via PIL defaults.
"""
from pathlib import Path

from PIL import Image

# Clockwise degrees -> exact transpose op.
_OPS = {90: Image.Transpose.ROTATE_270,
        180: Image.Transpose.ROTATE_180,
        270: Image.Transpose.ROTATE_90}


def rotate_image(img, degrees_cw):
    """`img` rotated by `degrees_cw` (clockwise, multiple of 90)
    via exact transposes — the viewer displays THIS function and
    the save path writes THIS function, so they cannot diverge."""
    deg = int(degrees_cw) % 360
    if deg == 0:
        return img
    return img.transpose(_OPS[deg])


def save_rotated(path, img, degrees_cw):
    """Write `img` rotated by `degrees_cw` back to `path` (same
    file, same format). Returns the degrees actually applied."""
    deg = int(degrees_cw) % 360
    if deg == 0:
        return 0
    out = rotate_image(img, deg)
    ext = Path(path).suffix.lower()
    if ext in (".jpg", ".jpeg"):
        out.convert("RGB").save(path, "JPEG", quality=100, subsampling=0)
    elif ext == ".webp":
        out.save(path, "WEBP", lossless=True)
    elif ext == ".png":
        out.save(path, "PNG")
    elif ext in (".bmp", ".tif", ".tiff", ".gif"):
        out.save(path)
    else:
        out.save(path)
    return deg
