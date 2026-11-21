#!/bin/bash
# Test gateway: run after EVERY change.
# Usage: bash scripts/gate.sh
set -e
cd "$(dirname "$0")/.."
# Prefer venv python if present, else python3 (needs pip install -r requirements.txt)
PY=python3
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; fi
echo "=== 1/2 check_lines (max 200) ==="
$PY scripts/check_lines.py
echo "=== 2/2 run_tests ($PY) ==="
$PY run_tests.py
echo "=== GATE PASSED ==="
