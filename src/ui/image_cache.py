"""Cross-rebuild PhotoImage cache (Round 24, item 8).

Both shell toggles (language, theme) destroy every widget and build
the whole UI again on the SAME root window, so a PhotoImage created
on that root stays valid across rebuilds - yet rounded.py /
rounded_frame.py / rounded_widgets.py re-rendered every PIL image
from scratch on each rebuild (the round-21 profile counted ~273
button renders + ~1,265 PhotoImage creations per rebuild, plus
paper re-tiling). This cache keeps the rendered PhotoImages on the
toplevel widget (the same pattern as tooth_image.py / logo.py), so
the cache dies with its Tk interpreter and can never hand an image
to a destroyed root.

KEY CONTRACT (correctness): callers pass a tuple whose first item
names the kind and which then carries w, h and EVERY other parameter
that determines the pixels (radius, fill / border colours, gradient
colour tuple, theme mode where the renderer depends on it). The key
is built at the render call site from the exact arguments handed to
the PIL renderer; a parameter missing from a key would be a stale
colour/text bug. Button TEXT is not in the button key on purpose:
Tk draws the label over the image (compound="center"), and the text
only influences the image through the measured (w, h), which ARE in
the key.

Bounded: at most MAX_ENTRIES entries and MAX_PIXELS total pixels
(w*h read from key[1] / key[2]); oldest entries evict first. The
toggle key space is small (2 languages x 2 themes x the app's fixed
widget sizes), so eviction is a safety valve, not the normal path.
Single images over MAX_IMAGE_PIXELS are NOT cached at all: layout
transients produce one-off giant sizes (a 2752x1947 paper tile was
measured during one build) that would evict the useful entries.
Widgets always keep their own reference to the image they display
(and RoundedButton keeps its previous set until _sync() repoints
it), so an evicted entry can never delete a displayed image.
"""
from collections import OrderedDict

from PIL import ImageTk

MAX_ENTRIES = 1024
MAX_PIXELS = 32_000_000  # ~128 MB of RGBA worst case, all sizes summed
MAX_IMAGE_PIXELS = 3_000_000  # bigger than any steady-state widget
_ATTR = "_r24_photo_cache"


def _cache_for(master):
    """The OrderedDict {key: (PhotoImage, pixels)} on master's root."""
    try:
        top = master.winfo_toplevel()
    except Exception:
        top = master
    cache = getattr(top, _ATTR, None)
    if cache is None:
        cache = OrderedDict()
        setattr(top, _ATTR, cache)
    return cache


def cached_photo(master, key, make_pil):
    """PhotoImage for `key`: make_pil() renders it on first use only;
    later calls (e.g. the next toggle rebuild) reuse the image.
    Created with master=master, like every PhotoImage in this app."""
    try:
        px = int(key[1]) * int(key[2])
    except Exception:
        px = 0
    if px > MAX_IMAGE_PIXELS:  # transient giant: render, don't cache
        return ImageTk.PhotoImage(make_pil(), master=master)
    cache = _cache_for(master)
    hit = cache.get(key)
    if hit is not None:
        cache.move_to_end(key)
        return hit[0]
    img = ImageTk.PhotoImage(make_pil(), master=master)
    cache[key] = (img, px)
    total = sum(p for _, p in cache.values())
    while len(cache) > 1 and (len(cache) > MAX_ENTRIES or total > MAX_PIXELS):
        _, (_, p) = cache.popitem(last=False)
        total -= p
    return img


def cache_size(master):
    """Entries currently cached for master's interpreter (tests)."""
    return len(_cache_for(master))
