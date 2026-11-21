#!/usr/bin/env python3
"""Fail if any .py >200 lines. Usage: python scripts/check_lines.py"""
import sys
from pathlib import Path
MAX_LINES = 200
ROOT = Path(__file__).resolve().parent.parent
bad = []
for p in sorted(ROOT.rglob("*.py")):
    if ".venv" in str(p) or "__pycache__" in str(p):
        continue
    n = len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
    status = "OK " if n <= MAX_LINES else "FAIL"
    print(f"{status} {n:4d}  {p.relative_to(ROOT)}")
    if n > MAX_LINES:
        bad.append((str(p), n))
if bad:
    print(f"\nFAIL: {len(bad)} file(s) exceed {MAX_LINES} lines")
    sys.exit(1)
print(f"\nPASS: all .py files <= {MAX_LINES} lines")
