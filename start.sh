#!/bin/bash
# Start Dota 2 Stats Flask Server

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_PATH="/c/Users/there/miniconda3/envs/dota2/python.exe"

echo "Starting Dota 2 Stats server..."
echo "Access at: http://127.0.0.1:5000"
echo "Press Ctrl+C to stop"
echo ""

cd "$SCRIPT_DIR"
"$PYTHON_PATH" app.py
