#!/bin/bash
# Stop Dota 2 Stats — FastAPI + Next.js

echo "Stopping Dota 2 Stats services..."

# Stop FastAPI (uvicorn)
pids=$(pgrep -f "uvicorn main:app" 2>/dev/null)
if [ -n "$pids" ]; then
    for pid in $pids; do
        echo "Killing FastAPI process $pid"
        kill "$pid" 2>/dev/null
    done
fi

# Stop Next.js (next dev)
pids=$(pgrep -f "next dev" 2>/dev/null)
if [ -n "$pids" ]; then
    for pid in $pids; do
        echo "Killing Next.js process $pid"
        kill "$pid" 2>/dev/null
    done
fi

# Also stop old Flask server if running
pids=$(pgrep -f "python.*app.py" 2>/dev/null)
if [ -n "$pids" ]; then
    for pid in $pids; do
        echo "Killing Flask process $pid"
        kill "$pid" 2>/dev/null
    done
fi

echo "Done."
