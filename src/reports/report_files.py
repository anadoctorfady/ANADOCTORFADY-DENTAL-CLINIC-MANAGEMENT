"""Round 16 worker C: saving + system printing of a generated PDF,
plus best-effort PDF inspection (page count / text) for the print
preview. Offline, no new dependencies. <200 lines.
"""
import re
import shutil
import subprocess
import sys
import zlib
from pathlib import Path
from src.reports.pdf_common import reports_dir
from src.utils.helpers import unique_report


def save_pdf_copy(src, dest_path=None):
    """Copy a generated PDF to its final place: an exact dest_path,
    or a unique ANADOCTORFADY_ name inside reports_dir()."""
    src = Path(src)
    if dest_path:
        dst = Path(dest_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
    else:
        dst = unique_report(src.stem.replace("ANADOCTORFADY_", "", 1),
                            reports_dir())
        dst = dst.with_suffix(".pdf")
    shutil.copy2(src, dst)
    return dst


def print_pdf_file(path):
    """Send a PDF to the system printer. Returns (status, message)
    with status in {"ok", "no-printer", "error"}; never raises.
    Windows: the default PDF handler's print verb. Elsewhere: lp,
    then lpr. Real OS printing is unproven on the target machine —
    see the round-16 worker-C report."""
    path = str(path)
    if sys.platform.startswith("win"):
        try:
            import os
            os.startfile(path, "print")  # noqa: S606 - user-chosen file
            return "ok", ""
        except Exception as e:
            return "error", str(e)
    for cmd in ("lp", "lpr"):
        exe = shutil.which(cmd)
        if not exe:
            continue
        try:
            r = subprocess.run([exe, path], capture_output=True,
                               text=True, timeout=60)
            if r.returncode == 0:
                return "ok", ""
            return "error", (r.stderr or r.stdout or "").strip()
        except Exception as e:
            return "error", str(e)
    return "no-printer", ""


def pdf_page_count(path):
    """Page count from raw PDF markers; 1 when it cannot be read."""
    try:
        raw = Path(path).read_bytes()
        return max(1, len(re.findall(rb"/Type\s*/Page[^s]", raw)))
    except OSError:
        return 1


def extract_pdf_text(path):
    """Best-effort text of a PDF for the preview fallback: pdftotext
    when installed, else literal strings from decompressed streams
    (readable for the Helvetica/English parts; Arabic TTFont glyphs
    do not round-trip through this path). Returns "" when nothing
    usable was found."""
    path = str(path)
    if shutil.which("pdftotext"):
        try:
            r = subprocess.run(["pdftotext", "-layout", path, "-"],
                               capture_output=True, text=True, timeout=30)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout
        except Exception:
            pass
    try:
        raw = Path(path).read_bytes()
    except OSError:
        return ""
    parts = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", raw, re.S):
        try:
            data = zlib.decompress(m.group(1))
        except Exception:
            continue
        for s in re.findall(rb"\((?:[^()\\]|\\.)*\)", data):
            try:
                txt = s[1:-1].decode("latin-1").encode("latin-1") \
                    .decode("unicode_escape")
            except Exception:
                continue
            # Round 19 hardening: this loop also matches byte runs
            # inside EMBEDDED FONT programs and CMap streams, which
            # used to reach the preview as control-character garbage
            # (the owner's "unintelligible symbols" in both languages
            # on Windows, where pdftotext does not exist). Keep only
            # plausible text: fully printable and holding a letter.
            if txt.strip() and txt.isprintable() \
                    and any(c.isalpha() for c in txt):
                parts.append(txt)
    return "\n".join(parts)
