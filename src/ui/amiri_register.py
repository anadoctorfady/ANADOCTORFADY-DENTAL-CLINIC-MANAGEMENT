"""Amiri font registration (split from amiri.py, R52 line cap).

ROUND 56: DISABLED, by the owner's decision. Amiri was reverted
-- the Arabic UI is back to Segoe UI (see amiri.py) -- so this
module must never register the private font and must never
report Amiri as available, on any machine (including one where
Amiri happens to be installed system-wide: the revert is
unconditional, so the Linux dev box and his Windows machine
render the same font). The bundled Amiri TTFs were removed
from assets/fonts/ in this round. _register_private() keeps
its name and signature so existing callers/tests keep working;
it always answers False. The old Windows AddFontResourceExW
body was deleted, not commented out.
"""
FAMILY = "Amiri"


def _register_private():
    """Round 56: always False -- private font registration is
    disabled (no AddFontResourceExW call, on any platform)."""
    return False


def amiri_available(root):
    """Round 56: always False -- Amiri is reverted, everywhere."""
    return False
