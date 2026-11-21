"""Round 30: editable centre logo — storage + PDF header helper.

Storage: setting key `centre_logo` holds the stored filename
(e.g. "centre_logo.png"); the image bytes are copied into the app
DATA_DIR under that fixed name (source extension kept among
png/jpg/jpeg, normalised to centre_logo.<ext>). Validation uses PIL
Image.open(...).verify(); an invalid file stores NOTHING (no file,
no setting change) and raises ValueError for the UI to show.

PDF: logo_flowable() returns a centred ReportLab Image sized to fit
max 38mm wide x 22mm high preserving aspect, or None when no valid
logo is set — callers prepend logo_header_flowables() so a missing
logo adds no gap or placeholder. <200 lines.
"""
import shutil
from pathlib import Path

from src.config.settings import DATA_DIR

SETTING_KEY = "centre_logo"
ALLOWED_EXTS = {".png", ".jpg", ".jpeg"}
MAX_W_MM, MAX_H_MM = 38.0, 22.0


def _get(key, default=""):
    from src.models.database import get_setting
    return get_setting(key, default)


def _set(key, value):
    from src.models.database import set_setting
    set_setting(key, value)


def get_logo_path():
    """Stored logo path, or None: setting set AND file exists."""
    name = str(_get(SETTING_KEY, "") or "").strip()
    if not name:
        return None
    p = DATA_DIR / name
    return p if p.is_file() else None


def set_logo(source_path):
    """Validate + copy `source_path` into DATA_DIR as centre_logo.<ext>.

    Returns the stored filename. Raises ValueError (storing nothing)
    when the extension is not png/jpg/jpeg or PIL cannot verify the
    file as an image."""
    src = Path(source_path)
    ext = src.suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise ValueError(f"unsupported logo extension: {ext or '(none)'}")
    from PIL import Image
    try:
        with Image.open(src) as im:
            im.verify()
    except Exception as e:
        raise ValueError(f"invalid logo image: {e}") from e
    stored = f"centre_logo{ext}"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Remove any previous logo stored under a different extension.
    for old_ext in ALLOWED_EXTS:
        old = DATA_DIR / f"centre_logo{old_ext}"
        if old_ext != ext and old.exists():
            try:
                old.unlink()
            except OSError:
                pass
    shutil.copy2(src, DATA_DIR / stored)
    _set(SETTING_KEY, stored)
    return stored


def clear_logo():
    """Remove the stored logo file (any extension) + the setting."""
    name = str(_get(SETTING_KEY, "") or "").strip()
    candidates = {DATA_DIR / name} if name else set()
    candidates |= {DATA_DIR / f"centre_logo{e}" for e in ALLOWED_EXTS}
    for p in candidates:
        try:
            if p.is_file():
                p.unlink()
        except OSError:
            pass
    _set(SETTING_KEY, "")


def logo_flowable():
    """Centred ReportLab Image for the stored logo, or None.

    Sized to fit MAX_W_MM x MAX_H_MM preserving aspect (from the PIL
    pixel size). A missing/corrupt file yields None, never a crash,
    so documents fall back to exactly the pre-round-30 header."""
    path = get_logo_path()
    if path is None:
        return None
    try:
        from PIL import Image as PILImage
        with PILImage.open(path) as im:
            w_px, h_px = im.size
        if w_px <= 0 or h_px <= 0:
            return None
        from reportlab.lib.units import mm
        from reportlab.platypus import Image as RLImage
        scale = min(MAX_W_MM / w_px, MAX_H_MM / h_px)
        flow = RLImage(str(path), width=w_px * scale * mm,
                       height=h_px * scale * mm)
        flow.hAlign = "CENTER"
        return flow
    except Exception:
        return None


def logo_header_flowables():
    """[logo, small spacer] when a logo is set, else [] (no gap)."""
    flow = logo_flowable()
    if flow is None:
        return []
    from reportlab.lib.units import mm
    from reportlab.platypus import Spacer
    return [flow, Spacer(1, 2 * mm)]
