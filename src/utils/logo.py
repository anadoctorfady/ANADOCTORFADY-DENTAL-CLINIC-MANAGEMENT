"""Logo helper: frozen-aware load, missing logo never crashes. <60 lines."""
import sys
from pathlib import Path
try:
    from PIL import Image, ImageTk
except Exception:  # Pillow missing: UI works without the logo
    Image = ImageTk = None

# Primary logo first: ANADOCTORFADY text baked in, transparent background.
_CANDIDATES = ("logo_anadoctorfady.png", "logo_transparent.png",
               "logo.png", "logo.jpg")


def _assets():
    # Frozen EXE: assets are bundled in _MEIPASS; dev: project assets/.
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", "")) / "assets"
    return Path(__file__).resolve().parent.parent.parent / "assets"


def logo_path(name="logo_anadoctorfady.png"):
    """Absolute path of a bundled logo file, or None if missing."""
    p = _assets() / name
    return p if p.is_file() else None


def photo(master, width=120, name=None):
    """Tk PhotoImage of the logo scaled to `width` px, or None.

    Keeps transparency (RGBA): the label behind it must use the panel/card
    background, never a black square. Caller must keep the returned object
    alive (e.g. self._logo_img). Returns None if Pillow/logo is missing.
    """
    if Image is None:
        return None
    names = (name,) if name else _CANDIDATES
    p = next((logo_path(n) for n in names if logo_path(n)), None)
    if not p:
        return None
    # Cache per top-level window: rebuilding the shell re-asked Pillow to
    # open + LANCZOS-resize the logo on every toggle (~15ms for the 120px
    # About logo). PhotoImages live on the Tk interpreter, so the cache
    # hangs off the toplevel and dies with it (a new App = a new Tk).
    try: top = master.winfo_toplevel()
    except Exception: top = master
    cache = getattr(top, "_logo_photo_cache", None)
    if cache is None: cache = top._logo_photo_cache = {}
    key = (str(p), width)
    if key in cache: return cache[key]
    try:
        im = Image.open(p).convert("RGBA")
        h = max(1, round(im.height * width / im.width))
        img = ImageTk.PhotoImage(im.resize((width, h), Image.LANCZOS), master=master)
    except Exception:
        return None
    cache[key] = img
    return img
