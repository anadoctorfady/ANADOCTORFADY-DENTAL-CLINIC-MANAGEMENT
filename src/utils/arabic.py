"""Arabic reshaping + bidi. <100 lines."""
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _r = arabic_reshaper.ArabicReshaper(
        configuration={'delete_harakat': False, 'support_ligatures': True})
    HAS = True
except ImportError:
    HAS, _r = False, None
def has_arabic(s):
    return any('\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F'
               for c in str(s))
def reshape(s):
    """Plain text only - never pass HTML tags. Returns joined RTL glyphs."""
    if not s or not HAS or not has_arabic(s):
        return str(s or "")
    try:
        return get_display(_r.reshape(str(s)))
    except Exception:
        return str(s)
def ar(s):
    return reshape(s)
def bidi_isolate(s):
    """Wrap Latin/numbers inside Arabic so order stays correct.
    Round 55: LRM (U+200E) on both sides, NOT the LRI/PDI
    isolates (U+2066..U+2069) -- those rendered as small visible
    marks around Latin runs under Windows Segoe UI on the owner's
    machine, while LRM is zero-width in every font Tk can use."""
    return "\u200e" + str(s) + "\u200e"
def mixed_ar(ar_text, latin):
    return f"{reshape(ar_text)} {bidi_isolate(latin)}"
