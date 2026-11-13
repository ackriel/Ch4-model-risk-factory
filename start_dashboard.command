#!/bin/bash
# Double-click in Finder to start the dashboard. Close this window (or press Ctrl+C) to stop it.
cd "$(dirname "$0")"
if [ ! -d .venv ]; then echo "Run setup_mac.command first."; read -r -p "Press Enter to close."; exit 1; fi
source .venv/bin/activate
( sleep 4; open "http://localhost:8501" ) &
streamlit run app.py --server.headless true --browser.gatherUsageStats false
