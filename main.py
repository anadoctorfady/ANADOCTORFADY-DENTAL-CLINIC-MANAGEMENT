#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ANADOCTORFADY v2 - entry only. Run: python main.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.models.database import init_db
from src.ui.shell import App
def main():
    init_db()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App().mainloop()
if __name__ == "__main__":
    main()
