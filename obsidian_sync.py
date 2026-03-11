"""
Obsidian Sync Module for Dota 2 Stats
Syncs match data and reports to Obsidian vault (iCloud)
"""

import os
from datetime import datetime
from pathlib import Path

# Obsidian Vault Paths
OBSIDIAN_VAULT_PATH = os.path.expanduser(
    "~/Library/Mobile Documents/iCloud~md~obsidian/Documents"
)
MATCHES_DIR = os.path.join(OBSIDIAN_VAULT_PATH, "30_Dota2_Lab", "31_Daily_Reports")
HISTORY_DIR = os.path.join(OBSIDIAN_VAULT_PATH, "30_Dota2_Lab", "32_Match_History")
HERO_DIR = os.path.join(OBSIDIAN_VAULT_PATH, "30_Dota2_Lab", "33_Hero_Strategy")

# Hero ID to Chinese name mapping
HEROES_CN = {
    1: "敌法师", 2: "斧王", 3: "祸乱之源", 4: "血魔", 5: "水晶室女",
    6: "卓尔游侠", 7: "撼地者", 8: "主宰", 9: "米拉娜", 10: "变体精灵",
    11: "影魔", 12: "幻影长矛手", 13: "帕克", 14: "帕吉", 15: "剃刀",
    16: "沙王", 17: "风暴之灵", 18: "斯温", 19: "小小", 20: "复仇之魂",
    21: "风行者", 22: "宙斯", 23: "昆卡", 25: "莉娜", 26: "莱恩",
    27: "暗影萨满", 28: "斯拉达", 29: "潮汐猎人", 30: "巫医", 31: "巫妖",
    32: "力丸", 33: "谜团", 34: "修补匠", 35: "狙击手", 36: "瘟疫法师",
    37: "术士", 38: "兽王", 39: "痛苦女王", 40: "剧毒术士",
    41: "虚空假面", 42: "冥魂大帝", 43: "死亡先知", 44: "幻影刺客",
    45: "帕格纳", 46: "圣堂刺客", 47: "冥界亚龙", 48: "露娜", 49: "龙骑士",
    50: "戴泽", 51: "发条技师", 52: "拉席克", 53: "先知", 54: "噬魂鬼",
    55: "黑暗贤者", 56: "克林克兹", 57: "全能骑士", 58: "魅惑魔女", 59: "哈斯卡",
    60: "暗夜魔王", 61: "育母蜘蛛", 62: "赏金猎人", 63: "编织者", 64: "杰奇洛",
    65: "蝙蝠骑士", 66: "陈", 67: "幽鬼", 68: "远古冰魄", 69: "末日使者",
    70: "熊战士", 71: "裂魂人", 72: "矮人直升机", 73: "炼金术士", 74: "祈求者",
    75: "沉默术士", 76: "殁境神蚀者", 77: "狼人", 78: "酒仙", 79: "暗影恶魔",
    80: "德鲁伊", 81: "混沌骑士", 82: "米波", 83: "树精卫士", 84: "食人魔魔法师",
    85: "不朽尸王", 86: "拉比克", 87: "干扰者", 88: "司夜刺客", 89: "娜迦海妖",
    90: "光之守卫", 91: "艾欧", 92: "维萨吉", 93: "斯拉克", 94: "美杜莎",
    95: "巨魔战将", 96: "半人马战行者", 97: "马格纳斯", 98: "伐木机",
    99: "钢背兽", 100: "巨牙海民", 101: "天怒法师", 102: "亚巴顿", 103: "上古巨神",
    104: "军团指挥官", 105: "工程师", 106: "灰烬之灵", 107: "大地之灵",
    108: "孽主", 109: "恐怖利刃", 110: "凤凰", 111: "神谕者", 112: "寒冬飞龙",
    113: "天穹守望者", 114: "齐天大圣", 119: "邪影芳灵", 120: "石鳞剑士",
    121: "天涯墨客", 123: "森海飞霞", 126: "虚无之灵", 128: "电炎绝手", 129: "玛尔斯",
    131: "马戏团长", 135: "破晓辰星", 136: "玛西", 137: "獸", 138: "琼英碧灵",
    145: "凯", 155: "朗戈"
}


def ensure_directories():
    """Create Obsidian directories if they don't exist."""
    os.makedirs(MATCHES_DIR, exist_ok=True)
    os.makedirs(HISTORY_DIR, exist_ok=True)
    os.makedirs(HERO_DIR, exist_ok=True)


def format_duration(seconds):
    """Format duration in minutes:seconds."""
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"


def determine_win(player_slot, radiant_win):
    """Determine if player won based on player_slot and radiant_win."""
    Radiant = player_slot < 128
    return (Radiant and radiant_win) or (not Radiant and not radiant_win)


def save_match_to_obsidian(match_data):
    """Save a single match to Obsidian as a markdown note.
    
    Args:
        match_data: dict with match information
    """
    ensure_directories()
    
    match_id = match_data.get("match_id", "unknown")
    hero_id = match_data.get("hero_id", 0)
    hero_cn = HEROES_CN.get(hero_id, "未知英雄")
    date = match_data.get("date", "")
    win = match_data.get("win", "Unknown")
    
    # Filename: 2026-02-15_敌法师_vs_[match_id].md
    win_indicator = "胜" if win == "Win" else "负"
    filename = f"{date[:10]}_{hero_cn}_{win_indicator}_{match_id}.md"
    
    # Check if already exists
    filepath = os.path.join(HISTORY_DIR, filename)
    if os.path.exists(filepath):
        return filepath
    
    # Create markdown content
    content = f"""---
date: {date}
tags: [Dota2, 比赛记录]
hero: {hero_cn}
result: {win}
---

# {hero_cn} - {win}

- **比赛ID**: {match_id}
- **日期**: {date}
- **结果**: {"✅ 胜利" if win == "Win" else "❌ 失败"}
- **英雄**: {hero_cn}

## 数据

| 项目 | 数据 |
|------|------|
| 击杀 | {match_data.get("kills", 0)} |
| 死亡 | {match_data.get("deaths", 0)} |
| 助攻 | {match_data.get("assists", 0)} |
| KDA | {match_data.get("kda", 0)} |
| 正补 | {match_data.get("last_hits", 0)} |
| GPM | {match_data.get("gpm", 0)} |
| XPM | {match_data.get("xpm", 0)} |
| 英雄伤害 | {match_data.get("hero_damage", 0)} |
| 塔伤害 | {match_data.get("tower_damage", 0)} |
| 持续时间 | {match_data.get("duration", "0:00")} |
| 模式 | {match_data.get("game_mode", "")} |
| 队列 | {match_data.get("lobby_type", "")} |

## 链接

- [OpenDota](https://www.opendota.com/matches/{match_id})

---
*自动同步自 Dota2 Stats*
"""
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"  📝 Saved match to Obsidian: {filename}")
    return filepath


def save_daily_report_to_obsidian(report_content, date_str=None):
    """Save daily report to Obsidian.
    
    Args:
        report_content: string, the report content
        date_str: optional date string, defaults to today
    """
    ensure_directories()
    
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    filename = f"每日战报_{date_str}.md"
    filepath = os.path.join(MATCHES_DIR, filename)
    
    # Add frontmatter
    full_content = f"""---
date: {date_str}
tags: [Dota2, 每日战报]
type: daily-report
---

{report_content}

---
*自动同步自 Dota2 Stats - 每日战报*
"""
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(full_content)
    
    print(f"  📝 Saved daily report to Obsidian: {filename}")
    return filepath


def sync_matches_batch(matches_list):
    """Sync multiple matches to Obsidian as a single combined file.
    Appends new matches while keeping existing ones.
    
    Args:
        matches_list: list of match_data dicts (new matches to add)
    
    Creates/updates a single 历史战绩.md file with all matches in table format.
    """
    ensure_directories()
    
    filepath = os.path.join(HISTORY_DIR, '历史战绩.md')
    existing_matches = {}
    
    # Read existing file if it exists
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse existing matches from markdown table
        for line in content.split('\n'):
            if line.startswith('| ') and '---' not in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 6 and parts[1] and parts[1] != '日期':
                    # Extract match ID from the line if available
                    date = parts[1]
                    hero = parts[2]
                    result = parts[3]
                    kda = parts[4]
                    duration = parts[5]
                    # Use date_hero as unique key, not parts[6] which can be empty
                    match_id = f"{date}_{hero}"
                    existing_matches[match_id] = {
                        'date': date,
                        'hero': hero,
                        'result': result,
                        'kda': kda,
                        'duration': duration
                    }
    
    # Add new matches
    new_count = 0
    for m in matches_list:
        hero_id = m.get('hero_id', 0)
        hero_cn = HEROES_CN.get(hero_id, '未知英雄')
        date = datetime.fromtimestamp(m.get('timestamp', 0)).strftime('%Y-%m-%d') if m.get('timestamp') else ''
        win = m.get('win', 'Unknown')
        win_emoji = '✅' if win == 'Win' else '❌'
        # Convert duration from seconds to mm:ss format
        duration_sec = m.get('duration', 0)
        if isinstance(duration_sec, int) and duration_sec > 0:
            minutes = duration_sec // 60
            seconds = duration_sec % 60
            duration = f"{minutes}:{seconds:02d}"
        else:
            duration = str(duration_sec) if duration_sec else '0:00'
        kda = f"{m.get('kills', 0)}/{m.get('deaths', 0)}/{m.get('assists', 0)}"
        match_id = f"{date}_{hero_cn}"
        
        if match_id not in existing_matches:
            existing_matches[match_id] = {
                'date': date,
                'hero': hero_cn,
                'result': win_emoji,
                'kda': kda,
                'duration': duration
            }
            new_count += 1
    
    # Sort by date (newest first)
    sorted_matches = sorted(existing_matches.values(), 
                          key=lambda x: x['date'], reverse=True)
    
    # Build table rows
    rows = []
    for m in sorted_matches:
        row = f"| {m['date']} | {m['hero']} | {m['result']} | {m['kda']} | {m['duration']} |"
        rows.append(row)
    
    # Create markdown content
    content = f'''---
title: Dota2 历史战绩
date: {datetime.now().strftime('%Y-%m-%d')}
tags: [Dota2, 历史战绩]
---

# Dota2 历史战绩 (共{len(sorted_matches)}场)

| 日期 | 英雄 | 结果 | K/D/A | 时长 |
|------|------|------|-------|------|
{chr(10).join(rows)}

---
*自动同步自 Dota2 Stats - 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
'''
    
    # Save to single file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  📝 Synced to Obsidian: 历史战绩.md (total: {len(sorted_matches)}, new: {new_count})")
    return len(sorted_matches)


if __name__ == "__main__":
    # Test
    ensure_directories()
    print(f"Obsidian Vault: {OBSIDIAN_VAULT_PATH}")
    print(f"Matches dir: {MATCHES_DIR}")
    print(f"History dir: {HISTORY_DIR}")
