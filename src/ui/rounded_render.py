"""PIL renderers for rounded widgets (Round 51: split out of
rounded.py for the 200-line cap; rounded.py re-exports both names).

rounded_pil: RGBA rounded rectangle, transparent corners. The
corners are drawn at 4x and downscaled -- a plain 1x PIL draw has
NO antialiasing, so corners rendered as visible staircases (R43).
R51: the downscale is Image.reduce (exact 4x4 area coverage --
the true antialiasing integral, and several times faster than the
old LANCZOS resize, whose ringing also pulled edge colours off
their true values). Fast path for large images: only the four
corner patches go through the 4x render + downscale; the body
(straight edges + uniform fill) is drawn at 1x, where a downscale
of a uniform region is the identity. The patches are composited
with alpha_composite (true source-over) over corner squares first
cleared to transparency, so the antialiased fringe matches the
full render; the patch seam sits in the uniform region past the
curve. Small images keep the full-supersample path.
"""
from PIL import Image, ImageDraw

from src.config.theme import GRADIENT

_SS = 4  # supersample factor for corner antialiasing (R43)
_FAST_MIN_PIXELS = 20000  # below this the legacy path is already fast


def _patch(w, h, r, fill, border, bw, corner):
    """One corner of the 4x rounded rect, rendered on a small canvas
    (the full rect drawn with shifted coordinates, PIL clips it),
    downscaled to 1x. Patch size s = r + _SS + 1 at 1x: the curve
    plus a margin, so the seam lands in uniform fill."""
    s = r + _SS + 1
    big = s * _SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    W, H = w * _SS - 1, h * _SS - 1
    if corner == "tl":
        box = [0, 0, W, H]
    elif corner == "tr":
        box = [-(W - (big - 1)), 0, big - 1, H]
    elif corner == "bl":
        box = [0, -(H - (big - 1)), W, big - 1]
    else:
        box = [-(W - (big - 1)), -(H - (big - 1)), big - 1, big - 1]
    ImageDraw.Draw(img).rounded_rectangle(
        box, radius=r * _SS, fill=fill, outline=border,
        width=(bw * _SS) if border else 1)
    return img.reduce(_SS), s


def rounded_pil(w, h, radius, fill, border=None, border_width=1):
    """RGBA image: rounded rectangle `fill`, transparent corners."""
    w, h = max(int(w), 1), max(int(h), 1)
    r = max(0, min(int(radius), w // 2, h // 2))
    s = r + _SS + 1
    if r > 0 and w >= 2 * s and h >= 2 * s and w * h >= _FAST_MIN_PIXELS:
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(img).rounded_rectangle(
            [0, 0, w - 1, h - 1], radius=r, fill=fill, outline=border,
            width=border_width if border else 1)
        for corner, (px, py) in (("tl", (0, 0)), ("tr", (w - s, 0)),
                                 ("bl", (0, h - s)), ("br", (w - s, h - s))):
            patch, _ = _patch(w, h, r, fill, border, border_width, corner)
            # Clear the body's corner square first: the patch then
            # composites over transparency, exactly as the full 4x
            # render antialiases the arc against transparent black.
            img.paste((0, 0, 0, 0), (px, py, px + s, py + s))
            region = img.crop((px, py, px + s, py + s))
            img.paste(Image.alpha_composite(region, patch), (px, py))
        return img
    img = Image.new("RGBA", (w * _SS, h * _SS), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle(
        [0, 0, w * _SS - 1, h * _SS - 1], radius=r * _SS, fill=fill,
        outline=border, width=(border_width * _SS) if border else 1)
    return img.reduce(_SS)


def gradient_pil(w, h, radius, colors=GRADIENT):
    """RGBA image: horizontal gradient across `colors`, rounded mask."""
    from PIL import ImageColor
    w, h = max(int(w), 1), max(int(h), 1)
    stops = [ImageColor.getrgb(c)[:3] for c in colors]
    n = len(stops)
    row = Image.new("RGB", (w, 1))
    px = row.load()
    for x in range(w):
        pos = (x / max(w - 1, 1)) * (n - 1)
        i = min(int(pos), n - 2); f = pos - i
        px[x, 0] = tuple(round(stops[i][k] + (stops[i + 1][k] - stops[i][k]) * f)
                         for k in range(3))
    base = row.resize((w, h)).convert("RGBA")
    mask = Image.new("L", (w * _SS, h * _SS), 0)  # AA mask, as rounded_pil
    r = max(0, min(int(radius), w // 2, h // 2))
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w * _SS - 1, h * _SS - 1],
                                           radius=r * _SS, fill=255)
    base.putalpha(mask.resize((w, h), Image.LANCZOS))
    return base
