"""
Dota 2 Stats Fetcher for vinceybb (Steam ID: 894447460)
Fetches match data from OpenDota API and saves to CSV files.
With Chinese hero names and MMR tracking.
"""

import requests
import csv
import os
from datetime import datetime
from pathlib import Path

STEAM_ID = 894447460
BASE_URL = "https://api.opendota.com/api"
DATA_DIR = Path(__file__).parent / "data"

# Hero ID to English name mapping
HEROES_EN = {
    1: "antimage", 2: "axe", 3: "bane", 4: "bloodseeker", 5: "crystal_maiden",
    6: "drow_ranger", 7: "earthshaker", 8: "juggernaut", 9: "mirana", 10: "morphling",
    11: "nevermore", 12: "phantom_lancer", 13: "puck", 14: "pudge", 15: "razor",
    16: "sand_king", 17: "storm_spirit", 18: "sven", 19: "tiny", 20: "vengefulspirit",
    21: "windrunner", 22: "zuus", 23: "kunkka", 25: "lina", 26: "lion",
    27: "shadow_shaman", 28: "slardar", 29: "tidehunter", 30: "witch_doctor", 31: "lich",
    32: "riki", 33: "enigma", 34: "tinker", 35: "sniper", 36: "necrolyte",
    37: "warlock", 38: "beastmaster", 39: "queenofpain", 40: "venomancer",
    41: "faceless_void", 42: "skeleton_king", 43: "death_prophet", 44: "phantom_assassin",
    45: "pugna", 46: "templar_assassin", 47: "viper", 48: "luna", 49: "dragon_knight",
    50: "dazzle", 51: "rattletrap", 52: "leshrac", 53: "furion", 54: "life_stealer",
    55: "dark_seer", 56: "clinkz", 57: "omniknight", 58: "enchantress", 59: "huskar",
    60: "night_stalker", 61: "broodmother", 62: "bounty_hunter", 63: "weaver", 64: "jakiro",
    65: "batrider", 66: "chen", 67: "spectre", 68: "ancient_apparition", 69: "doom_bringer",
    70: "ursa", 71: "spirit_breaker", 72: "gyrocopter", 73: "alchemist", 74: "invoker",
    75: "silencer", 76: "obsidian_destroyer", 77: "lycan", 78: "brewmaster", 79: "shadow_demon",
    80: "lone_druid", 81: "chaos_knight", 82: "meepo", 83: "treant", 84: "ogre_magi",
    85: "undying", 86: "rubick", 87: "disruptor", 88: "nyx_assassin", 89: "naga_siren",
    90: "keeper_of_the_light", 91: "wisp", 92: "visage", 93: "slark", 94: "medusa",
    95: "troll_warlord", 96: "centaur", 97: "magnataur", 98: "shredder",
    99: "bristleback", 100: "tusk", 101: "skywrath_mage", 102: "abaddon", 103: "elder_titan",
    104: "legion_commander", 105: "techies", 106: "ember_spirit", 107: "earth_spirit",
    108: "abyssal_underlord", 109: "terrorblade", 110: "phoenix", 111: "oracle", 112: "winter_wyvern",
    113: "arc_warden", 114: "monkey_king", 119: "dark_willow", 120: "pangolier",
    121: "grimstroke", 123: "hoodwink", 126: "void_spirit", 128: "snapfire", 129: "mars",
    131: "ringmaster", 135: "dawnbreaker", 136: "marci", 137: "primal_beast", 138: "muerta",
    145: "kez", 155: "largo"
}

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

GAME_MODES = {
    0: "未知", 1: "全选", 2: "队长模式", 3: "随机征召",
    4: "单选征召", 5: "全随机", 22: "天梯全选", 23: "加速模式"
}

LOBBY_TYPES = {
    0: "普通", 1: "练习", 2: "比赛", 4: "人机",
    5: "天梯组排", 6: "天梯单排", 7: "天梯", 8: "1v1中路", 9: "勇士联赛"
}


def get_hero_icon_url(hero_id):
    """Get hero icon URL from Dota 2 CDN."""
    hero_name = HEROES_EN.get(hero_id, "")
    if hero_name:
        return f"https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/{hero_name}.png"
    return ""


def ensure_data_dir():
    """Create data directory if it doesn't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def refresh_player_data():
    """Request OpenDota to refresh/parse new matches for the player."""
    url = f"{BASE_URL}/players/{STEAM_ID}/refresh"
    try:
        response = requests.post(url)
        if response.status_code == 200:
            print("Requested match refresh from OpenDota")
            return True
        else:
            print(f"Refresh request returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"Failed to request refresh: {e}")
        return False


def fetch_player_profile():
    """Fetch player profile information."""
    url = f"{BASE_URL}/players/{STEAM_ID}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def fetch_matches(limit=100):
    """Fetch match history. Use limit=None for all matches (slower)."""
    url = f"{BASE_URL}/players/{STEAM_ID}/matches"
    params = {"limit": limit} if limit else {}
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def fetch_recent_matches():
    """Fetch last 20 recent matches with more detail."""
    url = f"{BASE_URL}/players/{STEAM_ID}/recentMatches"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def fetch_match_details(match_id):
    """Fetch detailed match data including items."""
    url = f"{BASE_URL}/matches/{match_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def fetch_items():
    """Fetch item constants."""
    url = f"{BASE_URL}/constants/items"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def fetch_hero_stats():
    """Fetch per-hero statistics."""
    url = f"{BASE_URL}/players/{STEAM_ID}/heroes"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def fetch_totals():
    """Fetch aggregated totals (kills, deaths, assists, etc.)."""
    url = f"{BASE_URL}/players/{STEAM_ID}/totals"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def fetch_win_loss():
    """Fetch win/loss record."""
    url = f"{BASE_URL}/players/{STEAM_ID}/wl"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def determine_win(player_slot, radiant_win):
    """Determine if player won based on slot and radiant_win."""
    is_radiant = player_slot < 128
    return (is_radiant and radiant_win) or (not is_radiant and not radiant_win)


def format_duration(seconds):
    """Convert seconds to MM:SS format."""
    return f"{seconds // 60}:{seconds % 60:02d}"


def get_item_icon_url(item_id):
    """Get item icon URL."""
    if not item_id or item_id == 0:
        return ""
    return f"https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/items/{item_id}.png"


def fetch_matches_with_items(match_ids, max_matches=50):
    """Fetch detailed match data with items for recent matches."""
    import time
    results = []
    for i, match_id in enumerate(match_ids[:max_matches]):
        try:
            print(f"  Fetching match {i+1}/{min(len(match_ids), max_matches)}: {match_id}")
            details = fetch_match_details(match_id)
            # Find player data
            for player in details.get("players", []):
                if player.get("account_id") == STEAM_ID:
                    results.append({
                        "match_id": match_id,
                        "items": [
                            player.get("item_0", 0),
                            player.get("item_1", 0),
                            player.get("item_2", 0),
                            player.get("item_3", 0),
                            player.get("item_4", 0),
                            player.get("item_5", 0),
                        ],
                        "item_neutral": player.get("item_neutral", 0),
                        "backpack": [
                            player.get("backpack_0", 0),
                            player.get("backpack_1", 0),
                            player.get("backpack_2", 0),
                        ]
                    })
                    break
            time.sleep(0.5)  # Rate limiting
        except Exception as e:
            print(f"  Error fetching match {match_id}: {e}")
    return results


def load_existing_items():
    """Load existing match items from CSV."""
    filepath = DATA_DIR / "match_items.csv"
    if not filepath.exists():
        return {}
    items = {}
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            items[row["match_id"]] = {
                "match_id": row["match_id"],
                "items": [
                    int(row.get("item_0", 0) or 0),
                    int(row.get("item_1", 0) or 0),
                    int(row.get("item_2", 0) or 0),
                    int(row.get("item_3", 0) or 0),
                    int(row.get("item_4", 0) or 0),
                    int(row.get("item_5", 0) or 0),
                ],
                "item_neutral": int(row.get("item_neutral", 0) or 0)
            }
    return items


def save_match_items_csv(items_data, filename="match_items.csv"):
    """Save match items to CSV."""
    ensure_data_dir()
    filepath = DATA_DIR / filename

    fieldnames = ["match_id", "item_0", "item_1", "item_2", "item_3", "item_4", "item_5", "item_neutral"]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for item in items_data:
            row = {
                "match_id": item["match_id"],
                "item_0": item["items"][0],
                "item_1": item["items"][1],
                "item_2": item["items"][2],
                "item_3": item["items"][3],
                "item_4": item["items"][4],
                "item_5": item["items"][5],
                "item_neutral": item["item_neutral"]
            }
            writer.writerow(row)

    print(f"Saved items for {len(items_data)} matches to {filepath}")


def save_matches_csv(matches, filename="matches.csv"):
    """Save match data to CSV."""
    ensure_data_dir()
    filepath = DATA_DIR / filename

    fieldnames = [
        "match_id", "date", "timestamp", "hero", "hero_cn", "hero_id", "hero_icon",
        "win", "kills", "deaths", "assists", "kda", "last_hits", "gpm", "xpm",
        "hero_damage", "tower_damage", "hero_healing", "duration", "game_mode",
        "lobby_type", "party_size", "avg_rank"
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for m in matches:
            win = determine_win(m.get("player_slot", 0), m.get("radiant_win", False))
            deaths = m.get("deaths", 0)
            kda = (m.get("kills", 0) + m.get("assists", 0)) / max(deaths, 1)
            hero_id = m.get("hero_id")

            row = {
                "match_id": m.get("match_id"),
                "date": datetime.fromtimestamp(m.get("start_time", 0)).strftime("%Y-%m-%d %H:%M"),
                "timestamp": m.get("start_time", 0),
                "hero": HEROES_EN.get(hero_id, f"unknown"),
                "hero_cn": HEROES_CN.get(hero_id, f"未知英雄"),
                "hero_id": hero_id,
                "hero_icon": get_hero_icon_url(hero_id),
                "win": "Win" if win else "Loss",
                "kills": m.get("kills", 0),
                "deaths": deaths,
                "assists": m.get("assists", 0),
                "kda": round(kda, 2),
                "last_hits": m.get("last_hits", 0),
                "gpm": m.get("gold_per_min", 0),
                "xpm": m.get("xp_per_min", 0),
                "hero_damage": m.get("hero_damage", 0),
                "tower_damage": m.get("tower_damage", 0),
                "hero_healing": m.get("hero_healing", 0),
                "duration": format_duration(m.get("duration", 0)),
                "game_mode": GAME_MODES.get(m.get("game_mode"), str(m.get("game_mode"))),
                "lobby_type": LOBBY_TYPES.get(m.get("lobby_type"), str(m.get("lobby_type"))),
                "party_size": m.get("party_size", ""),
                "avg_rank": m.get("average_rank", "")
            }
            writer.writerow(row)

    print(f"Saved {len(matches)} matches to {filepath}")


def save_hero_stats_csv(hero_stats, filename="hero_stats.csv"):
    """Save per-hero statistics to CSV."""
    ensure_data_dir()
    filepath = DATA_DIR / filename

    fieldnames = ["hero", "hero_cn", "hero_id", "hero_icon", "games", "wins", "win_rate"]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for h in hero_stats:
            hero_id = int(h.get("hero_id", 0))
            games = h.get("games", 0)
            wins = h.get("win", 0)
            if games == 0:
                continue

            row = {
                "hero": HEROES_EN.get(hero_id, "unknown"),
                "hero_cn": HEROES_CN.get(hero_id, "未知英雄"),
                "hero_id": hero_id,
                "hero_icon": get_hero_icon_url(hero_id),
                "games": games,
                "wins": wins,
                "win_rate": round(wins / games * 100, 1) if games > 0 else 0
            }
            writer.writerow(row)

    print(f"Saved hero stats to {filepath}")


def save_profile_csv(profile, wl, current_mmr=None, filename="profile.csv"):
    """Save player profile to CSV."""
    ensure_data_dir()
    filepath = DATA_DIR / filename

    p = profile.get("profile", {})
    fieldnames = ["field", "value"]

    # Use provided MMR or estimated MMR
    mmr = current_mmr if current_mmr else profile.get("computed_mmr")

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        data = [
            ("username", p.get("personaname")),
            ("steam_id", STEAM_ID),
            ("rank_tier", profile.get("rank_tier")),
            ("current_mmr", mmr),
            ("estimated_mmr", profile.get("computed_mmr")),
            ("country", p.get("loccountrycode")),
            ("total_wins", wl.get("win", 0)),
            ("total_losses", wl.get("lose", 0)),
            ("win_rate", round(wl.get("win", 0) / max(wl.get("win", 0) + wl.get("lose", 0), 1) * 100, 1)),
            ("last_updated", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        ]

        for field, value in data:
            writer.writerow({"field": field, "value": value})

    print(f"Saved profile to {filepath}")


def update_mmr_history(mmr, win_result=None):
    """Append MMR to history file for trend tracking."""
    ensure_data_dir()
    filepath = DATA_DIR / "mmr_history.csv"

    file_exists = filepath.exists()

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["date", "mmr", "result"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            mmr,
            win_result or ""
        ])

    print(f"Updated MMR history: {mmr}")


def load_mmr_history():
    """Load MMR history from file."""
    filepath = DATA_DIR / "mmr_history.csv"
    if not filepath.exists():
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def update_all(match_limit=500, current_mmr=None, fetch_items=False):
    """Fetch all data and save to CSV files."""
    import time

    # Request OpenDota to parse new matches first
    print("Requesting OpenDota to refresh match data...")
    refresh_player_data()
    # Wait a bit for OpenDota to process the refresh request
    print("Waiting for OpenDota to process...")
    time.sleep(3)

    print("Fetching player profile...")
    profile = fetch_player_profile()
    wl = fetch_win_loss()
    save_profile_csv(profile, wl, current_mmr)

    # Update MMR history if provided
    if current_mmr:
        update_mmr_history(current_mmr)

    print(f"\nFetching last {match_limit} matches...")
    matches = fetch_matches(limit=match_limit)
    save_matches_csv(matches)

    print("\nFetching hero statistics...")
    hero_stats = fetch_hero_stats()
    save_hero_stats_csv(hero_stats)

    # Load existing items and find new matches without items
    existing_items = load_existing_items()
    recent_match_ids = [str(m.get("match_id")) for m in matches[:50]]
    new_match_ids = [mid for mid in recent_match_ids if mid not in existing_items]

    # Always fetch items for new matches (up to 20 at a time to be fast)
    if new_match_ids:
        print(f"\nFetching items for {len(new_match_ids)} new matches...")
        new_items_data = fetch_matches_with_items(new_match_ids, max_matches=min(len(new_match_ids), 20))

        # Merge with existing items
        for item in new_items_data:
            existing_items[str(item["match_id"])] = item

        # Save all items
        all_items = list(existing_items.values())
        save_match_items_csv(all_items)

    # If fetch_items flag is set, refresh all recent items
    if fetch_items:
        print("\nRefreshing items for all recent matches...")
        match_ids = [m.get("match_id") for m in matches[:50]]
        items_data = fetch_matches_with_items(match_ids, max_matches=50)
        save_match_items_csv(items_data)

    print("\nDone! CSV files saved to:", DATA_DIR)


def quick_update():
    """Fetch only recent matches (faster)."""
    print("Fetching recent matches...")
    matches = fetch_recent_matches()
    save_matches_csv(matches, "recent_matches.csv")
    print("Done!")


def backfill_items(batch_size=20):
    """Fetch items for all matches that don't have item data yet."""
    import time

    # Load all matches
    matches_file = DATA_DIR / "matches.csv"
    if not matches_file.exists():
        print("No matches.csv found. Run update_all first.")
        return

    all_match_ids = []
    with open(matches_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_match_ids.append(row["match_id"])

    # Load existing items
    existing_items = load_existing_items()

    # Find matches without items
    missing_ids = [mid for mid in all_match_ids if mid not in existing_items]

    if not missing_ids:
        print("All matches already have item data!")
        return

    print(f"Found {len(missing_ids)} matches without item data.")
    print(f"Fetching items in batches of {batch_size}...")

    total_fetched = 0
    for i in range(0, len(missing_ids), batch_size):
        batch = missing_ids[i:i + batch_size]
        print(f"\nBatch {i // batch_size + 1}: Fetching items for {len(batch)} matches...")

        items_data = fetch_matches_with_items(batch, max_matches=len(batch))

        # Merge with existing items
        for item in items_data:
            existing_items[str(item["match_id"])] = item

        total_fetched += len(items_data)

        # Save after each batch
        all_items = list(existing_items.values())
        save_match_items_csv(all_items)

        print(f"Progress: {total_fetched}/{len(missing_ids)} matches processed")

        # Rate limiting between batches
        if i + batch_size < len(missing_ids):
            print("Waiting before next batch...")
            time.sleep(2)

    print(f"\nDone! Fetched items for {total_fetched} matches.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        quick_update()
    elif len(sys.argv) > 1 and sys.argv[1] == "--mmr":
        # Update with current MMR: python fetch_dota_stats.py --mmr 3651
        if len(sys.argv) > 2:
            try:
                mmr = int(sys.argv[2])
                update_all(match_limit=200, current_mmr=mmr)
            except ValueError:
                print("Invalid MMR value")
        else:
            print("Usage: python fetch_dota_stats.py --mmr <mmr_value>")
    elif len(sys.argv) > 1 and sys.argv[1] == "--items":
        # Fetch with items: python fetch_dota_stats.py --items
        update_all(match_limit=200, fetch_items=True)
    elif len(sys.argv) > 1 and sys.argv[1] == "--backfill":
        # Backfill items for all matches: python fetch_dota_stats.py --backfill
        backfill_items()
    else:
        limit = 500
        if len(sys.argv) > 1:
            try:
                limit = int(sys.argv[1])
            except ValueError:
                pass
        update_all(match_limit=limit)
