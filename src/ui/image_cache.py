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

Bounded, in TWO tiers (Round 52): small images (buttons and other
widgets up to SMALL_PX pixels) and large ones (rounded-frame panels)
evict independently, so a burst of big panel renders can never flush
the button working set and vice versa. The toggle key space is
2 languages x 2 themes x the app's widget sizes; Round 51's single
1024-entry / 32M-pixel cache sat AT both caps after every toggle and
thrashed (a warm toggle re-rendered as much as a cold one) -- the
tier budgets below hold the full 4-combination working set with
headroom, and eviction remains a safety valve, not the normal path.
Single images over MAX_IMAGE_PIXELS are NOT cached at all: layout
transients produce one-off giant sizes (a 2752x1947 paper tile was
measured during one build) that would evict the useful entries.
Widgets always keep their own reference to the image they display
(and RoundedButton keeps its previous set until _sync() repoints
it), so an evicted entry can never delete a displayed image.
"""
from collections import OrderedDict

from PIL import ImageTk

SMALL_PX = 65_536  # <= 256x256: buttons, pills, small tiles
SMALL_MAX_ENTRIES = 8192
SMALL_MAX_PIXELS = 48_000_000
LARGE_MAX_ENTRIES = 256
LARGE_MAX_PIXELS = 64_000_000
MAX_IMAGE_PIXELS = 3_000_000  # bigger than any steady-state widget
_ATTR = "_r24_photo_cache"


def _cache_for(master):
    """{'s': OrderedDict, 'l': OrderedDict} on master's root:
    {key: (PhotoImage, pixels)} per tier."""
    try:
        top = master.winfo_toplevel()
    except Exception:
        top = master
    cache = getattr(top, _ATTR, None)
    if cache is None:
        cache = {"s": OrderedDict(), "l": OrderedDict()}
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
    tiers = _cache_for(master)
    if px <= SMALL_PX:
        cache, max_n, max_px = tiers["s"], SMALL_MAX_ENTRIES, SMALL_MAX_PIXELS
    else:
        cache, max_n, max_px = tiers["l"], LARGE_MAX_ENTRIES, LARGE_MAX_PIXELS
    hit = cache.get(key)
    if hit is not None:
        cache.move_to_end(key)
        return hit[0]
    img = ImageTk.PhotoImage(make_pil(), master=master)
    cache[key] = (img, px)
    total = sum(p for _, p in cache.values())
    while len(cache) > 1 and (len(cache) > max_n or total > max_px):
        _, (_, p) = cache.popitem(last=False)
        total -= p
    return img


def cache_size(master):
    """Entries currently cached for master's interpreter (tests)."""
    tiers = _cache_for(master)
    return len(tiers["s"]) + len(tiers["l"])
