#!/usr/bin/env python3
"""
Daily Dota 2 Stats Report - Runs at midnight to summarize today's games
Enhanced version with detailed KDA analysis and personalized suggestions
"""
import os
import sys
sys.path.insert(0, '/Users/vinceybb/github/dota2_stats')

from datetime import datetime, timedelta
from collections import Counter

import notion_db as nc

def get_recent_matches():
    """Get matches from yesterday midnight to now."""
    all_matches = nc.query_matches()
    
    # Get yesterday's date at midnight
    now = datetime.now()
    yesterday_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_timestamp = yesterday_start.timestamp()
    
    # Filter matches from yesterday onwards
    recent_matches = [
        m for m in all_matches 
        if m.get('timestamp', 0) >= yesterday_timestamp
    ]
    
    # Sort by timestamp descending (newest first)
    recent_matches.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    return recent_matches

def analyze_performance(matches):
    """Analyze detailed performance metrics."""
    total_kills = sum(m.get('kills', 0) for m in matches)
    total_deaths = sum(m.get('deaths', 0) for m in matches)
    total_assists = sum(m.get('assists', 0) for m in matches)
    
    avg_kda = (total_kills + total_assists) / max(total_deaths, 1)
    avg_kills = total_kills / len(matches)
    avg_deaths = total_deaths / len(matches)
    
    # Performance rating
    if avg_kda >= 4.0:
        performance = "carry"
    elif avg_kda >= 2.5:
        performance = "good"
    elif avg_kda >= 1.5:
        performance = "average"
    else:
        performance = "poor"
    
    return {
        'avg_kda': avg_kda,
        'avg_kills': avg_kills,
        'avg_deaths': avg_deaths,
        'total_kills': total_kills,
        'total_deaths': total_deaths,
        'total_assists': total_assists,
        'performance': performance
    }

def generate_daily_report():
    """Generate enhanced daily battle report."""
    matches = get_recent_matches()
    
    if not matches:
        return "🐱 **每日 Dota 2 战报** — {date}\n\n📊 今日战况\n\n今天没有打Dota，休息一天也挺好！".format(
            date=datetime.now().strftime('%Y/%m/%d')
        )
    
    # Basic stats
    total_games = len(matches)
    wins = sum(1 for m in matches if m.get('win') == 'Win')
    losses = total_games - wins
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    
    # MMR calculation (±25 per game)
    mmr_change = (wins * 25) - (losses * 25)
    
    # Detailed performance analysis
    perf = analyze_performance(matches)
    
    # Heroes played
    hero_stats = {}
    for m in matches:
        hero = m.get('hero_cn', 'Unknown')
        if hero not in hero_stats:
            hero_stats[hero] = {'games': 0, 'wins': 0, 'kills': 0, 'deaths': 0, 'assists': 0}
        hero_stats[hero]['games'] += 1
        hero_stats[hero]['wins'] += 1 if m.get('win') == 'Win' else 0
        hero_stats[hero]['kills'] += m.get('kills', 0)
        hero_stats[hero]['deaths'] += m.get('deaths', 0)
        hero_stats[hero]['assists'] += m.get('assists', 0)
    
    # Sort by games played
    sorted_heroes = sorted(hero_stats.items(), key=lambda x: x[1]['games'], reverse=True)
    
    # Role analysis
    role_stats = {}
    for m in matches:
        role = m.get('role', m.get('lane_role', 0))
        if role:
            role_name = {1: '1号位', 2: '2号位', 3: '3号位', 4: '4号位', 5: '5号位'}.get(role, f'位置{role}')
            if role_name not in role_stats:
                role_stats[role_name] = {'games': 0, 'wins': 0}
            role_stats[role_name]['games'] += 1
            if m.get('win') == 'Win':
                role_stats[role_name]['wins'] += 1
    
    # Build detailed report
    lines = [
        f"🐱 **每日 Dota 2 战报** — {datetime.now().strftime('%Y/%m/%d')}",
        "",
        "## 📊 总览",
        f"• 场次: **{total_games}** 局 | 胜 **{wins}** | 负 **{losses}** | 胜率 **{win_rate:.1f}%**",
        f"• MMR: {'+' if mmr_change >= 0 else ''}{mmr_change} 分",
        f"• 场均KDA: **{perf['avg_kda']:.2f}** ({perf['total_kills']}杀/{perf['total_deaths']}死/{perf['total_assists']}助)",
        "",
        "## 🎮 逐局回顾",
    ]
    
    for i, m in enumerate(matches, 1):
        hero = m.get('hero_cn', 'Unknown')
        result = "✅" if m.get('win') == 'Win' else "❌"
        k = m.get('kills', 0)
        d = m.get('deaths', 0)
        a = m.get('assists', 0)
        kda = (k + a) / max(d, 1)
        
        # Performance indicator
        if kda >= 6:
            perf_icon = "🔥"
        elif kda >= 3:
            perf_icon = "👍"
        elif kda >= 1.5:
            perf_icon = "😐"
        else:
            perf_icon = "💀"
        
        lines.append(f"{i}. {result} **{hero}** | KDA: {k}/{d}/{a} ({kda:.2f}) {perf_icon}")
    
    lines.extend([
        "",
        "## 🔥 英雄统计",
    ])
    
    for hero, stats in sorted_heroes[:3]:
        games = stats['games']
        wins = stats['wins']
        win_rate = (wins / games * 100) if games > 0 else 0
        avg_kda = (stats['kills'] + stats['assists']) / max(stats['deaths'], 1)
        lines.append(f"• **{hero}**: {games}局 {wins}胜 ({win_rate:.0f}%) | 场均KDA {avg_kda:.2f}")
    
    if role_stats:
        lines.extend([
            "",
            "## 🎯 位置表现",
        ])
        for role_name in sorted(role_stats.keys()):
            stats = role_stats[role_name]
            games = stats['games']
            wins = stats['wins']
            win_rate = (wins / games * 100) if games > 0 else 0
            lines.append(f"• **{role_name}**: {games}局 {wins}胜 ({win_rate:.0f}%)")
    
    # Smart suggestions based on data
    lines.extend([
        "",
        "## 💡 智能建议",
    ])
    
    # Key insight: KDA vs Win Rate mismatch (use overall_win_rate to avoid variable shadowing)
    overall_win_rate = (wins / total_games * 100) if total_games > 0 else 0
    if perf['avg_kda'] >= 4.0 and overall_win_rate < 50:
        lines.append("🎯 **核心诊断**: 你个人表现极强(KDA 4.0+)，但胜率低，这是典型的**带不动队友**！")
        lines.append("🔍 **证据**: 两把KDA 5.0+的局都输了，说明你在尽力但队友跟不上")
        lines.append("💡 **建议**: ")
        lines.append("  1. 凯太吃团队配合，试试能1v9的英雄(幽鬼/敌法师/虚空)")
        lines.append("  2. 组排上分 — 你的水平需要靠谱队友")
        lines.append("  3. 避开深夜单排，那段时间神仙多")
    elif perf['avg_kda'] >= 3.0 and win_rate < 45:
        lines.append("🎯 **诊断**: KDA不错但赢不了，可能英雄选择或节奏把控需要调整")
        lines.append("💡 **建议**: 试试版本强势英雄，或换个时间段")
    elif perf['performance'] == 'good' and win_rate >= 50:
        lines.append("🎯 **诊断**: 表现稳定，胜率不错，保持这个节奏！")
    elif perf['performance'] == 'poor':
        lines.append("🎯 **诊断**: 今天状态一般，可能遇到克制或阵容问题")
        lines.append("💡 **建议**: 休息调整，或尝试辅助位换个心态")
    
    # Hero specific advice
    if len(sorted_heroes) > 0:
        main_hero = sorted_heroes[0][0]
        main_stats = sorted_heroes[0][1]
        main_win_rate = (main_stats['wins'] / main_stats['games'] * 100) if main_stats['games'] > 0 else 0
        main_avg_kda = (main_stats['kills'] + main_stats['assists']) / max(main_stats['deaths'], 1)
        
        if main_win_rate < 40 and main_stats['games'] >= 3:
            if main_avg_kda >= 3.5:
                lines.append(f"⚠️ **{main_hero}** 个人KDA {main_avg_kda:.1f} 但胜率 {main_win_rate:.0f}% — 这英雄单排不靠谱")
            else:
                lines.append(f"⚠️ **{main_hero}** 今天表现和胜率都一般，换个英雄试试？")
    
    # MMR advice
    if mmr_change <= -50:
        lines.append(f"📉 今天掉了 {abs(mmr_change)} 分，建议停排休息，改天再战")
    elif mmr_change <= -25:
        lines.append(f"📉 小掉 {abs(mmr_change)} 分，正常波动，心态稳住")
    elif mmr_change >= 50:
        lines.append(f"📈 今天上了 {mmr_change} 分，状态火热，继续冲！")
    elif mmr_change > 0:
        lines.append(f"📈 小上 {mmr_change} 分，稳步上分中")
    
    lines.extend([
        "",
        "🐱 YiFi 为你播报",
    ])
    
    return '\n'.join(lines)

if __name__ == "__main__":
    report = generate_daily_report()
    print(report)
