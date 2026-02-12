#!/bin/bash
# Daily Dota 2 Report - Sends report to Discord at midnight

# Change to dota2_stats directory
cd /Users/vinceybb/github/dota2_stats

# Generate report and save to temp file
REPORT=$(python3 daily_report.py 2>/dev/null)

# Send to Discord using OpenClaw message tool
# The report will be sent to the configured Discord channel
echo "$REPORT" | python3 << 'PYEOF'
import sys
import json
import requests

report = sys.stdin.read()

# Use OpenClaw's messaging API or write to a file that can be picked up
# For now, we'll write to a temp file that can be read by the agent
with open('/tmp/dota2_daily_report.txt', 'w') as f:
    f.write(report)

print("Report saved to /tmp/dota2_daily_report.txt")
PYEOF
