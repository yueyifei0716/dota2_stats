#!/usr/bin/env python3
"""
Daily Dota 2 Stats Report - Runs at midnight to summarize today's games
"""
import os
import sys
sys.path.insert(0, '/Users/vinceybb/github/dota2_stats')

from datetime import datetime, timedelta
from collections import Counter

import notion_db as nc

def get_today_matches():
    """Get matches from today (since midnight)."""
    all_matches = nc.query_matches()
    
    # Get today's date at midnight
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_timestamp = today_start.timestamp()
    
    # Filter matches from today
    today_matches = [
        m for m in all_matches 
        if m.get('timestamp', 0) >= today_timestamp
    ]
    
    return today_matches

def generate_daily_report():
    """Generate daily battle report."""
    matches = get_today_matches()
    
    if not matches:
        return "📊 今日战况\n\n今天没有打Dota，休息一天也挺好！"
    
    # Basic stats
    total_games = len(matches)
    wins = sum(1 for m in matches if m.get('win') == 'Win')
    losses = total_games - wins
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    
    # MMR calculation (±25 per game)
    mmr_change = (wins * 25) - (losses * 25)
    
    # Heroes played
    hero_counts = Counter(m.get('hero_cn', 'Unknown') for m in matches)
    top_heroes = hero_counts.most_common(5)
    
    # Role analysis
    role_wins = {}
    role_games = {}
    for m in matches:
        role = m.get('role', m.get('lane_role', 0))
        if role:
            role_name = {1: '1号位', 2: '2号位', 3: '3号位', 4: '4号位', 5: '5号位'}.get(role, f'位置{role}')
            role_games[role_name] = role_games.get(role_name, 0) + 1
            if m.get('win') == 'Win':
                role_wins[role_name] = role_wins.get(role_name, 0) + 1
    
    # Build report
    report_lines = [
        "🎮 **今日Dota战况汇报**",
        f"📅 {datetime.now().strftime('%Y-%m-%d')}",
        "",
        f"📊 **总览**",
        f"• 总场次: {total_games} 局",
        f"• 胜利: {wins} 局 | 失败: {losses} 局",
        f"• 胜率: {win_rate:.1f}%",
        f"• MMR变化: {'+' if mmr_change >= 0 else ''}{mmr_change} 分",
        "",
        f"🔥 **常用英雄**",
    ]
    
    for hero, count in top_heroes:
        hero_wins = sum(1 for m in matches if m.get('hero_cn') == hero and m.get('win') == 'Win')
        hero_wr = (hero_wins / count * 100) if count > 0 else 0
        report_lines.append(f"• {hero}: {count}局 ({hero_wins}胜, {hero_wr:.0f}%)")
    
    if role_games:
        report_lines.extend([
            "",
            f"🎯 **位置表现**",
        ])
        for role_name in sorted(role_games.keys()):
            games = role_games[role_name]
            wins_in_role = role_wins.get(role_name, 0)
            wr = (wins_in_role / games * 100) if games > 0 else 0
            report_lines.append(f"• {role_name}: {games}局 ({wins_in_role}胜, {wr:.0f}%)")
    
    # Suggestions based on performance
    report_lines.extend([
        "",
        f"💡 **今日建议**",
    ])
    
    if win_rate >= 60:
        report_lines.append("• 今天状态不错！继续保持这个节奏 🚀")
    elif win_rate < 40:
        report_lines.append("• 今天运气不太好，建议休息调整心态 😤")
    
    if mmr_change >= 50:
        report_lines.append(f"• 今天上了 {mmr_change} 分，上分如喝水！💪")
    elif mmr_change <= -50:
        report_lines.append(f"• 今天掉了 {abs(mmr_change)} 分，建议复盘一下关键局 🤔")
    
    # Hero suggestions
    if top_heroes:
        best_hero = top_heroes[0][0]
        report_lines.append(f"• 今天'{best_hero}'玩得最多，可以继续练习这个英雄 ✨")
    
    report_lines.extend([
        "",
        "🐱 YiFi 为你播报",
    ])
    
    return '\n'.join(report_lines)

if __name__ == "__main__":
    report = generate_daily_report()
    print(report)
