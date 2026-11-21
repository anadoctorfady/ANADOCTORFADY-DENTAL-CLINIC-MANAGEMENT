"""Helpers: filenames, nationalities, tooth numbers. <120 lines."""
import re
from pathlib import Path
from datetime import datetime
INVALID = r'[\\/*?:"<>|:]'
def sanitize(name):
    name = re.sub(INVALID, "_", str(name)).replace("/", "_").strip()
    return (name or "patient")[:100]
def unique_report(base, directory, file_number=None, ext=".pdf"):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    cand = directory / f"ANADOCTORFADY_{sanitize(base)}{ext}"
    if not cand.exists():
        return cand
    if file_number:
        cand = directory / f"ANADOCTORFADY_{sanitize(base)}_{file_number}{ext}"
        if not cand.exists():
            return cand
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return directory / f"ANADOCTORFADY_{sanitize(base)}_{ts}{ext}"
try:
    from src.utils.nationalities import list_nationalities, display as _nat_display
    NATIONALITIES = [_nat_display(i) for i in list_nationalities()]
except Exception:
    NATIONALITIES = ["Syrian", "Lebanese", "Jordanian",
        "Iraqi", "Egyptian", "Saudi", "Other"]
PERMANENT = ["11","12","13","14","15","16","17","18",
    "21","22","23","24","25","26","27","28",
    "31","32","33","34","35","36","37","38",
    "41","42","43","44","45","46","47","48"]
DECIDUOUS = ["51","52","53","54","55","61","62","63","64","65",
    "71","72","73","74","75","81","82","83","84","85"]
def is_permanent(n):
    return n in PERMANENT
# Alias for v1 name
unique_report_filename = unique_report
