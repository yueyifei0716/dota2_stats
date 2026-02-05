#!/bin/bash
# Stop Dota 2 Stats Flask Server

echo "Stopping Dota 2 Stats server..."

# Find and kill Flask processes running app.py
pids=$(ps aux 2>/dev/null | grep "[p]ython.*app.py" | awk '{print $2}')
if [ -z "$pids" ]; then
    # Try Windows-style process list
    pids=$(tasklist 2>/dev/null | grep -i python | awk '{print $2}')
fi

if [ -n "$pids" ]; then
    for pid in $pids; do
        echo "Killing process $pid"
        kill $pid 2>/dev/null || taskkill //PID $pid //F 2>/dev/null
    done
    echo "Server stopped."
else
    echo "No running server found."
fi
