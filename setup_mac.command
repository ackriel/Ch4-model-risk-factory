#!/bin/bash
# Double-click in Finder to set up the Model Risk Factory on a Mac (one time).
cd "$(dirname "$0")"
LOG="setup_log.txt"
{
echo "== Model Risk Factory setup - $(date) =="
PY=""
for c in python3.13 python3.12 python3.11 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo "ERROR: Python 3.11 or newer was not found."
  echo "Install it from https://www.python.org/downloads/macos/ and double-click this file again."
  echo "SETUP_RESULT=NO_PYTHON"
else
  echo "Using $PY ($($PY --version))"
  "$PY" -m venv .venv && source .venv/bin/activate \
    && python -m pip install --upgrade pip -q \
    && pip install -r requirements.txt \
    && python main.py setup \
    && python -m pytest -q \
    && echo "SETUP_RESULT=OK" || echo "SETUP_RESULT=FAILED"
fi
} 2>&1 | tee "$LOG"
echo
echo "Done. If you see SETUP_RESULT=OK, double-click start_dashboard.command to open the dashboard."
read -r -p "Press Enter to close this window."
