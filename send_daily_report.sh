#!/bin/bash
# Daily Dota 2 Report - Generate report + push to WeChat via Server酱
# Usage: Add to crontab: 0 0 * * * /Users/vinceybb/github/dota2_stats/send_daily_report.sh

cd /Users/vinceybb/github/dota2_stats

# Activate conda environment and run report with WeChat push
eval "$(conda shell.bash hook)"
conda activate dota2

# Generate yesterday's report (runs at midnight, so report on the day that just ended)
YESTERDAY=$(date -v-1d +%Y-%m-%d)
python3 daily_report.py "$YESTERDAY" --wechat
