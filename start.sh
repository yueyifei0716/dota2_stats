#!/bin/bash
# Start Dota 2 Stats — FastAPI + Next.js

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"

if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

echo "Starting Dota 2 Stats..."
echo ""

# Start FastAPI backend
echo "Starting FastAPI (port 8000)..."
cd "$SCRIPT_DIR/api"
"$PYTHON_BIN" -m uvicorn main:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!
echo "  FastAPI PID: $FASTAPI_PID"

# Start Next.js frontend
echo "Starting Next.js (port 3000)..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
NEXTJS_PID=$!
echo "  Next.js PID: $NEXTJS_PID"

echo ""
echo "Dashboard: http://localhost:3000"
echo "API:       http://localhost:8000/api/health"
echo ""
echo "Press Ctrl+C to stop both services"

# Wait for both processes; stop both on Ctrl+C
trap "kill $FASTAPI_PID $NEXTJS_PID 2>/dev/null; exit 0" INT TERM
wait
