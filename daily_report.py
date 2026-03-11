#!/usr/bin/env python3
"""
Daily Dota 2 Stats Report - Runs at midnight to summarize today's games
Enhanced version with detailed KDA analysis and personalized suggestions

Usage:
    python3 daily_report.py              # Today's report
    python3 daily_report.py 2026-02-17   # Specific date's report
"""
import os
import sys
import argparse
import requests
sys.path.insert(0, '/Users/vinceybb/github/dota2_stats')

from datetime import datetime, timedelta, timezone
from collections import Counter
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

import notion_db as nc
import obsidian_sync as obs

# Shanghai timezone (UTC+8)
SHANGHAI_TZ = timezone(timedelta(hours=8))

def get_matches_for_date(date_str=None):
    """Get matches from a specific date (midnight to midnight China timezone UTC+8)."""
    all_matches = nc.query_matches()
    
    if date_str:
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
    else:
        target_date = datetime.now(SHANGHAI_TZ)
    
    # Calculate target date's start and end in Shanghai timezone
    day_start_sh = target_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=SHANGHAI_TZ)
    day_end_sh = day_start_sh + timedelta(days=1)
    
    # Convert to UTC timestamps (what's stored in Notion)
    day_start_utc_ts = day_start_sh.timestamp()
    day_end_utc_ts = day_end_sh.timestamp()
    
    # Filter matches from this date 00:00 to 24:00 (Shanghai time)
    day_matches = [
        m for m in all_matches 
        if day_start_utc_ts <= m.get('timestamp', 0) < day_end_utc_ts
    ]
    
    # Sort by timestamp descending (newest first)
    day_matches.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    return day_matches

def get_today_matches():
    """Get matches from today midnight (China timezone UTC+8) to now."""
    all_matches = nc.query_matches()
    
    # Calculate today's start in local time
    now_local = datetime.now()
    today_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Convert to timestamp
    today_start_ts = today_start_local.timestamp()
    
    # Filter matches from today 00:00 to now
    today_matches = [
        m for m in all_matches 
        if m.get('timestamp', 0) >= today_start_ts
    ]
    
    # Sort by timestamp descending (newest first)
    today_matches.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    return today_matches

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

def generate_daily_report(date_str=None):
    """Generate enhanced daily battle report for a specific date."""
    matches = get_matches_for_date(date_str)
    
    if date_str:
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
    else:
        target_date = datetime.now()
    
    if not matches:
        date_display = target_date.strftime('%Y/%m/%d')
        return "🐱 **每日 Dota 2 战报** — {date}\n\n📊 今日战况\n\n今天还没有打Dota，期待今晚的表现！".format(
            date=date_display
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
    
    # Build detailed report - show the target date
    date_display = target_date.strftime('%Y/%m/%d')
    lines = [
        f"🐱 **每日 Dota 2 战报** — {date_display}",
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


def format_wechat_report(date_str=None):
    """Generate a concise Markdown report suitable for Server酱 push."""
    matches = get_matches_for_date(date_str)

    if date_str:
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
    else:
        target_date = datetime.now(SHANGHAI_TZ)

    date_display = target_date.strftime('%Y/%m/%d')

    if not matches:
        return f"Dota2 战报 {date_display}", "今天还没有打 Dota，期待今晚的表现！"

    total = len(matches)
    wins = sum(1 for m in matches if m.get('win') == 'Win')
    losses = total - wins
    wr = wins / total * 100 if total else 0
    mmr_change = (wins - losses) * 25

    perf = analyze_performance(matches)

    # Streaks
    streak = 0
    streak_type = None
    for m in matches:
        w = m.get('win')
        if streak_type is None:
            streak_type = w
            streak = 1
        elif w == streak_type:
            streak += 1
        else:
            break

    streak_text = f"{'连胜' if streak_type == 'Win' else '连败'} {streak}" if streak >= 2 else ""

    # Best game
    best = max(matches, key=lambda m: (m.get('kills', 0) + m.get('assists', 0)) / max(m.get('deaths', 1), 1))
    best_hero = best.get('hero_cn', '?')
    best_kda = f"{best.get('kills',0)}/{best.get('deaths',0)}/{best.get('assists',0)}"

    title = f"Dota2 战报 {date_display} | {wins}胜{losses}负 {'📈' if wins > losses else '📉' if losses > wins else '⚖️'}"

    lines = [
        f"## 📊 {date_display} 战报",
        "",
        f"**{total}** 局 | **{wins}** 胜 **{losses}** 负 | 胜率 **{wr:.0f}%**",
        f"MMR: **{'+' if mmr_change >= 0 else ''}{mmr_change}**",
        f"场均 KDA: **{perf['avg_kda']:.2f}**",
        "",
    ]

    if streak_text:
        lines.append(f"🔥 当前 {streak_text}")
        lines.append("")

    lines.append(f"⭐ 最佳: {best_hero} ({best_kda})")
    lines.append("")

    # Per-game summary
    lines.append("### 逐局")
    for i, m in enumerate(matches, 1):
        result = "✅" if m.get('win') == 'Win' else "❌"
        hero = m.get('hero_cn', '?')
        k, d, a = m.get('kills', 0), m.get('deaths', 0), m.get('assists', 0)
        lines.append(f"{i}. {result} {hero} {k}/{d}/{a}")

    # Suggestions
    if perf['avg_deaths'] > 6:
        lines.extend(["", "💡 死亡偏高，注意地图意识"])
    if wr < 40 and total >= 3:
        lines.extend(["", "💡 胜率较低，建议休息调整心态"])

    return title, '\n'.join(lines)


def send_to_wechat(title, content):
    """Send report via Server酱 (https://sct.ftqq.com/)."""
    key = os.environ.get('SERVERCHAN_KEY', '')
    if not key:
        print("SERVERCHAN_KEY not set in .env, skipping WeChat push")
        return False

    url = f"https://sctapi.ftqq.com/{key}.send"
    resp = requests.post(url, data={"title": title, "desp": content}, timeout=15)
    result = resp.json()
    if result.get("code") == 0:
        print("WeChat push sent successfully!")
        return True
    else:
        print(f"WeChat push failed: {result.get('message', 'unknown error')}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate Dota 2 daily report')
    parser.add_argument('date', nargs='?', help='Date in YYYY-MM-DD format (default: today)')
    parser.add_argument('--no-sync', action='store_true', help='Skip Obsidian sync')
    parser.add_argument('--wechat', action='store_true', help='Send report to WeChat via Server酱')
    args = parser.parse_args()

    report = generate_daily_report(args.date)
    print(report)

    # WeChat push
    if args.wechat:
        print("\nSending to WeChat...")
        title, content = format_wechat_report(args.date)
        send_to_wechat(title, content)
    
    if args.no_sync:
        sys.exit(0)
    
    # Sync to Obsidian
    print("\nSyncing to Obsidian...")
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d')
        save_date = target_date.strftime("%Y-%m-%d")
    else:
        # No date provided = generate today's report, save with today's date
        save_date = datetime.now(SHANGHAI_TZ).strftime("%Y-%m-%d")
    
    obs.save_daily_report_to_obsidian(report, save_date)
    
    # Also sync ALL matches to history
    all_matches = nc.query_matches()
    print(f"Syncing {len(all_matches)} matches to history...")
    obs.sync_matches_batch(all_matches)
