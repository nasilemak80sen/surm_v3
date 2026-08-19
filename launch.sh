#!/bin/bash
# SURM Toolkit Launcher — Mac/Linux
# Usage: chmod +x launch.sh && ./launch.sh

echo ""
echo " ====================================================="
echo "  SURM Toolkit - PETRONAS Carigali"
echo "  Subsurface Uncertainty & Risk Management Plan"
echo " ====================================================="
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python 3 not found. Install from https://python.org"
    exit 1
fi

# Create venv if missing
if [ ! -d ".venv" ]; then
    echo "[SETUP] Creating virtual environment..."
    python3 -m venv .venv
    echo "[SETUP] Installing dependencies (first run only)..."
    source .venv/bin/activate
    pip install -r requirements.txt --quiet
    echo "[SETUP] Setup complete."
else
    source .venv/bin/activate
fi

# Open browser
(sleep 3 && python3 -c "import webbrowser; webbrowser.open('http://localhost:8501')") &

echo "[START] Launching SURM Toolkit at http://localhost:8501"
echo "        Press Ctrl+C to stop."
echo ""

streamlit run surm.py --server.port 8501 --browser.gatherUsageStats false
