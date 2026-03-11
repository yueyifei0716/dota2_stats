"""
Dota 2 Stats Fetcher for vinceybb (Steam ID: 894447460)
Fetches match data from OpenDota API and saves to Notion databases.
With Chinese hero names and MMR tracking.
"""

import requests
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for notion_client import
sys.path.insert(0, str(Path(__file__).parent))

import notion_db as nc
import obsidian_sync as obs

# Default timeout for all API requests
REQUEST_TIMEOUT = 10

STEAM_ID = 894447460
BASE_URL = "https://api.opendota.com/api"

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


def refresh_player_data():
    """Request OpenDota to refresh/parse new matches for the player."""
    url = f"{BASE_URL}/players/{STEAM_ID}/refresh"
    try:
        response = requests.post(url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            print("Requested match refresh from OpenDota")
            return True
        else:
            print(f"Refresh request returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"Failed to request refresh: {e}")
        return False


def request_match_parse(match_ids):
    """Request OpenDota to parse matches (needed for lane_role data).

    Args:
        match_ids: list of match ID strings to request parsing for
    Returns:
        number of successfully requested parses
    """
    import time
    requested = 0
    for mid in match_ids:
        try:
            url = f"{BASE_URL}/request/{mid}"
            response = requests.post(url, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                requested += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"  Failed to request parse for {mid}: {e}")
    return requested


def fetch_player_profile():
    """Fetch player profile information."""
    url = f"{BASE_URL}/players/{STEAM_ID}"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_player_ratings():
    """Fetch player rank tier history over time."""
    url = f"{BASE_URL}/players/{STEAM_ID}/ratings"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_player_rankings():
    """Fetch player hero rankings (percentile vs all players)."""
    url = f"{BASE_URL}/players/{STEAM_ID}/rankings"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_matches(limit=100):
    """Fetch match history. Use limit=None for all matches (slower)."""
    url = f"{BASE_URL}/players/{STEAM_ID}/matches"
    params = {"limit": limit} if limit else {}
    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_recent_matches():
    """Fetch last 20 recent matches with more detail."""
    url = f"{BASE_URL}/players/{STEAM_ID}/recentMatches"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_match_details(match_id):
    """Fetch detailed match data including items."""
    url = f"{BASE_URL}/matches/{match_id}"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def compute_role(account_id, teammates):
    """Compute Pos 1-5 using lane assignment + farm priority.

    Algorithm:
    1. lane_role=2 (mid) → Pos 2
    2. lane_role=3 (offlane) → Pos 3
    3. lane_role=1 (safe lane): highest last_hits → Pos 1, lowest → Pos 5
    4. lane_role=4 or is_roaming → Pos 4
    5. Remaining unassigned → fill by GPM rank
    Falls back to pure GPM ranking if lane_role data is mostly missing.
    """
    # Check if lane_role data is available (at least 3 teammates have it)
    has_lane = sum(1 for p in teammates if p.get("lane_role", 0) != 0)
    if has_lane < 3:
        # Fall back to GPM ranking
        ranked = sorted(teammates, key=lambda p: p.get("gold_per_min", 0), reverse=True)
        for i, p in enumerate(ranked, 1):
            if p.get("account_id") == account_id:
                return i
        return 0

    roles = {}  # account_id -> role
    used_roles = set()

    # Group by lane_role
    by_lane = {}
    for p in teammates:
        lr = p.get("lane_role", 0)
        by_lane.setdefault(lr, []).append(p)

    # Mid (lane_role=2) → Pos 2
    for p in by_lane.get(2, []):
        aid = p.get("account_id")
        if aid not in roles and 2 not in used_roles:
            roles[aid] = 2
            used_roles.add(2)

    # Offlane (lane_role=3) → Pos 3
    for p in by_lane.get(3, []):
        aid = p.get("account_id")
        if aid not in roles and 3 not in used_roles:
            roles[aid] = 3
            used_roles.add(3)

    # Safe lane (lane_role=1): highest last_hits → Pos 1, lowest → Pos 5
    safe = sorted(by_lane.get(1, []), key=lambda p: p.get("last_hits", 0), reverse=True)
    for i, p in enumerate(safe):
        aid = p.get("account_id")
        if aid in roles:
            continue
        if i == 0 and 1 not in used_roles:
            roles[aid] = 1
            used_roles.add(1)
        elif 5 not in used_roles:
            roles[aid] = 5
            used_roles.add(5)

    # Jungle/Roaming (lane_role=4 or is_roaming) → Pos 4
    jungle_roam = by_lane.get(4, []) + [p for p in teammates if p.get("is_roaming") and p.get("account_id") not in roles]
    for p in jungle_roam:
        aid = p.get("account_id")
        if aid not in roles and 4 not in used_roles:
            roles[aid] = 4
            used_roles.add(4)

    # Fill remaining unassigned by GPM
    unassigned = [p for p in teammates if p.get("account_id") not in roles]
    unassigned.sort(key=lambda p: p.get("gold_per_min", 0), reverse=True)
    available = sorted(r for r in [1, 2, 3, 4, 5] if r not in used_roles)
    for p, r in zip(unassigned, available):
        roles[p.get("account_id")] = r

    return roles.get(account_id, 0)


def fetch_match_advanced_data(match_id):
    """Fetch advanced match data for analytics (lane, benchmarks, gold advantage)."""
    details = fetch_match_details(match_id)

    # Find player data
    player_data = None
    player_team = None  # True = Radiant, False = Dire
    all_players = details.get("players", [])

    for player in all_players:
        if player.get("account_id") == STEAM_ID:
            player_data = player
            player_team = player.get("player_slot", 0) < 128  # Radiant if slot < 128
            break

    if not player_data:
        return None

    # Get gold/xp advantage arrays (from team perspective)
    radiant_gold_adv = details.get("radiant_gold_adv", [])
    radiant_xp_adv = details.get("radiant_xp_adv", [])

    # Calculate max gold lead/deficit from player's team perspective
    if player_team:  # Radiant
        gold_adv = radiant_gold_adv
    else:  # Dire - invert the values
        gold_adv = [-x for x in radiant_gold_adv] if radiant_gold_adv else []

    max_gold_lead = max(gold_adv) if gold_adv else 0
    max_gold_deficit = min(gold_adv) if gold_adv else 0

    # Determine throw/comeback
    won = determine_win(player_data.get("player_slot", 0), details.get("radiant_win", False))
    is_comeback = won and max_gold_deficit < -5000  # Won after being 5k behind
    is_throw = not won and max_gold_lead > 5000  # Lost after being 5k ahead

    # Get benchmarks
    benchmarks = player_data.get("benchmarks", {})

    # Compute role (Pos 1-5) using lane + farm priority
    teammates = [p for p in all_players if (p.get("player_slot", 0) < 128) == player_team]
    role = compute_role(STEAM_ID, teammates)

    # Get ally and enemy heroes
    ally_heroes = []
    enemy_heroes = []
    for p in all_players:
        if p.get("account_id") == STEAM_ID:
            continue
        p_team = p.get("player_slot", 0) < 128
        if p_team == player_team:
            ally_heroes.append(p.get("hero_id", 0))
        else:
            enemy_heroes.append(p.get("hero_id", 0))

    return {
        "match_id": match_id,
        "role": role,
        "lane_role": player_data.get("lane_role", 0),
        "lane": player_data.get("lane", 0),
        "is_roaming": player_data.get("is_roaming", False),
        "net_worth": player_data.get("net_worth", 0),
        "level": player_data.get("level", 0),
        "gold_spent": player_data.get("gold_spent", 0),
        "hero_damage": player_data.get("hero_damage", 0),
        "tower_damage": player_data.get("tower_damage", 0),
        "kills": player_data.get("kills", 0),
        "deaths": player_data.get("deaths", 0),
        "assists": player_data.get("assists", 0),
        "max_gold_lead": max_gold_lead,
        "max_gold_deficit": max_gold_deficit,
        "is_comeback": is_comeback,
        "is_throw": is_throw,
        "benchmark_gpm_pct": round(benchmarks.get("gold_per_min", {}).get("pct", 0) * 100, 1),
        "benchmark_xpm_pct": round(benchmarks.get("xp_per_min", {}).get("pct", 0) * 100, 1),
        "benchmark_kills_pct": round(benchmarks.get("kills_per_min", {}).get("pct", 0) * 100, 1),
        "benchmark_damage_pct": round(benchmarks.get("hero_damage_per_min", {}).get("pct", 0) * 100, 1),
        "benchmark_tower_pct": round(benchmarks.get("tower_damage", {}).get("pct", 0) * 100, 1),
        "ally_heroes": ",".join(map(str, ally_heroes)),
        "enemy_heroes": ",".join(map(str, enemy_heroes)),
    }


def fetch_items():
    """Fetch item constants."""
    url = f"{BASE_URL}/constants/items"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_hero_stats():
    """Fetch per-hero statistics."""
    url = f"{BASE_URL}/players/{STEAM_ID}/heroes"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_totals():
    """Fetch aggregated totals (kills, deaths, assists, etc.)."""
    url = f"{BASE_URL}/players/{STEAM_ID}/totals"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_win_loss():
    """Fetch win/loss record."""
    url = f"{BASE_URL}/players/{STEAM_ID}/wl"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_peers():
    """Fetch peers (teammates) data."""
    url = f"{BASE_URL}/players/{STEAM_ID}/peers"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_hero_matchups(hero_id):
    """Fetch hero matchups (counters and advantages) for a specific hero."""
    url = f"{BASE_URL}/heroes/{hero_id}/matchups"
    response = requests.get(url, timeout=30)
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
    """Load existing match IDs that have item data from Notion."""
    matches = nc.query_matches()
    items = {}
    for m in matches:
        if m.get("item_0", 0) != 0 or m.get("item_1", 0) != 0:
            items[str(m["match_id"])] = {
                "match_id": m["match_id"],
                "items": [m.get(f"item_{i}", 0) for i in range(6)],
                "item_neutral": m.get("item_neutral", 0),
            }
    return items


def save_match_items(items_data):
    """Save match items to Notion (update existing match pages)."""
    for item in items_data:
        mid = str(item["match_id"])
        nc.update_match_items(mid, item)
    print(f"Saved items for {len(items_data)} matches to Notion")


def load_existing_advanced_data():
    """Load existing match IDs that have advanced data from Notion."""
    matches = nc.query_matches()
    data = {}
    for m in matches:
        # Consider match as having advanced data only if lane_role is set
        if m.get("lane_role", 0) != 0:
            data[str(m["match_id"])] = m
    return data


def save_match_advanced(advanced_data_list):
    """Save advanced match data to Notion (update existing match pages)."""
    for adv in advanced_data_list:
        if isinstance(adv, dict) and "match_id" in adv:
            nc.update_match_advanced(str(adv["match_id"]), adv)
    print(f"Saved advanced data for {len(advanced_data_list)} matches to Notion")


def save_matches(matches):
    """Save match data to Notion (skip existing match IDs).
    Also auto-updates MMR based on win/loss (±25 per game).

    Returns:
        set: Hero IDs from newly saved matches (for incremental hero stats update)
    """
    existing_ids = nc.get_existing_match_ids()
    new_count = 0
    new_hero_ids = set()
    new_matches_for_mmr = []  # Track new matches for MMR auto-update

    for m in matches:
        match_id = str(m.get("match_id"))
        if match_id in existing_ids:
            continue

        win = determine_win(m.get("player_slot", 0), m.get("radiant_win", False))
        deaths = m.get("deaths", 0)
        kda = (m.get("kills", 0) + m.get("assists", 0)) / max(deaths, 1)
        hero_id = m.get("hero_id")

        match_data = {
            "match_id": match_id,
            "date": datetime.fromtimestamp(m.get("start_time", 0)).strftime("%Y-%m-%d %H:%M"),
            "timestamp": m.get("start_time", 0),
            "hero": HEROES_EN.get(hero_id, "unknown"),
            "hero_cn": HEROES_CN.get(hero_id, "未知英雄"),
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
            "avg_rank": m.get("average_rank", ""),
            "lane_role": m.get("lane_role", 0),
        }
        nc.create_match(match_data)
        new_count += 1
        new_hero_ids.add(hero_id)

        # Only track ranked matches for MMR (lobby_type 7 = ranked)
        lobby_type = m.get("lobby_type", 0)
        if lobby_type == 7:
            new_matches_for_mmr.append({
                "timestamp": m.get("start_time", 0),
                "win": win,
                "match_id": match_id,
            })

    # Auto-update MMR for new ranked matches
    if new_matches_for_mmr:
        auto_update_mmr(new_matches_for_mmr)

    print(f"Saved {new_count} new matches to Notion (skipped {len(matches) - new_count} existing)")
    
    # Sync new matches to Obsidian
    new_matches_for_obsidian = [m for m in matches if str(m.get("match_id")) not in existing_ids]
    if new_matches_for_obsidian:
        print("\nSyncing to Obsidian...")
        obs.sync_matches_batch(new_matches_for_obsidian)
    
    return new_hero_ids


def save_hero_stats(hero_stats, updated_hero_ids=None):
    """Save per-hero statistics to Notion.

    Args:
        hero_stats: Full hero stats from OpenDota API
        updated_hero_ids: If provided, only update these heroes (for incremental updates)
    """
    count = 0
    for h in hero_stats:
        hero_id = int(h.get("hero_id", 0))
        games = h.get("games", 0)
        wins = h.get("win", 0)
        if games == 0:
            continue

        # Skip if not in updated list (when doing incremental update)
        if updated_hero_ids is not None and hero_id not in updated_hero_ids:
            continue

        nc.upsert_hero_stat({
            "hero": HEROES_EN.get(hero_id, "unknown"),
            "hero_cn": HEROES_CN.get(hero_id, "未知英雄"),
            "hero_id": hero_id,
            "hero_icon": get_hero_icon_url(hero_id),
            "games": games,
            "wins": wins,
            "win_rate": round(wins / games * 100, 1) if games > 0 else 0,
        })
        count += 1
    print(f"Saved {count} hero stats to Notion")


def auto_update_mmr(new_ranked_matches):
    """Auto-update MMR based on new ranked match results.
    Uses ±25 as default MMR change per game.
    Only processes ranked matches (lobby_type 7).
    """
    MMR_CHANGE = 25  # Default MMR change per ranked game

    # Get current MMR from profile
    profile_data = nc.get_profile()
    current_mmr = profile_data.get("current_mmr", 0)
    if not current_mmr:
        print("No current MMR found, skipping auto MMR update")
        return

    # Sort by timestamp ascending (oldest first) to process in order
    new_ranked_matches.sort(key=lambda x: x["timestamp"])

    mmr = current_mmr
    for match in new_ranked_matches:
        if match["win"]:
            mmr += MMR_CHANGE
            result = "Win"
        else:
            mmr -= MMR_CHANGE
            result = "Loss"
        update_mmr_history(mmr, result)
        print(f"  Auto MMR: {result} → {mmr} (match {match['match_id']})")

    # Update profile with new estimated MMR
    nc.update_profile({"current_mmr": mmr, "estimated_mmr": mmr})
    print(f"Auto MMR updated: {current_mmr} → {mmr} ({len(new_ranked_matches)} ranked games)")


def save_profile(profile, wl, current_mmr=None):
    """Save player profile to Notion."""
    p = profile.get("profile", {})
    mmr = current_mmr if current_mmr else profile.get("computed_mmr")
    total_wins = wl.get("win", 0)
    total_losses = wl.get("lose", 0)

    nc.update_profile({
        "username": p.get("personaname"),
        "steam_id": STEAM_ID,
        "rank_tier": profile.get("rank_tier"),
        "current_mmr": mmr,
        "estimated_mmr": profile.get("computed_mmr"),
        "country": p.get("loccountrycode", ""),
        "total_wins": total_wins,
        "total_losses": total_losses,
        "win_rate": round(total_wins / max(total_wins + total_losses, 1) * 100, 1),
    })
    print(f"Saved profile to Notion")


def update_mmr_history(mmr, win_result=None):
    """Append MMR to Notion history database."""
    nc.append_mmr_history(mmr, win_result or "")
    print(f"Updated MMR history: {mmr}")


def load_mmr_history():
    """Load MMR history from Notion."""
    return nc.query_mmr_history()


def update_all(match_limit=500, current_mmr=None, fetch_items=False):
    """Fetch all data and save to Notion databases."""
    import time

    # Request OpenDota to parse new matches first
    print("Requesting OpenDota to refresh match data...")
    refresh_player_data()
    print("Waiting for OpenDota to process...")
    time.sleep(3)

    print("Fetching player profile...")
    profile = fetch_player_profile()
    wl = fetch_win_loss()
    save_profile(profile, wl, current_mmr)

    # Update MMR history if provided
    if current_mmr:
        update_mmr_history(current_mmr)

    print(f"\nFetching last {match_limit} matches...")
    matches = fetch_matches(limit=match_limit)
    new_hero_ids = save_matches(matches)

    # Only update hero stats for heroes that appeared in new matches
    if new_hero_ids:
        print(f"\nFetching hero statistics (updating {len(new_hero_ids)} heroes)...")
        hero_stats = fetch_hero_stats()
        save_hero_stats(hero_stats, updated_hero_ids=new_hero_ids)
    else:
        print("\nNo new matches, skipping hero stats update")

    # Load existing items and find new matches without items
    existing_items = load_existing_items()
    recent_match_ids = [str(m.get("match_id")) for m in matches[:50]]
    new_match_ids = [mid for mid in recent_match_ids if mid not in existing_items]

    # Always fetch items for new matches (up to 20 at a time to be fast)
    if new_match_ids:
        print(f"\nFetching items for {len(new_match_ids)} new matches...")
        new_items_data = fetch_matches_with_items(new_match_ids, max_matches=min(len(new_match_ids), 20))
        save_match_items(new_items_data)

    # If fetch_items flag is set, refresh all recent items
    if fetch_items:
        print("\nRefreshing items for all recent matches...")
        match_ids = [m.get("match_id") for m in matches[:50]]
        items_data = fetch_matches_with_items(match_ids, max_matches=50)
        save_match_items(items_data)

    # Fetch advanced data (lane_role, benchmarks, etc.) for new matches
    existing_advanced = load_existing_advanced_data()
    new_adv_ids = [mid for mid in recent_match_ids if mid not in existing_advanced]
    if new_adv_ids:
        # Request parsing first so lane_role data is available
        print(f"\nRequesting OpenDota to parse {len(new_adv_ids)} matches...")
        request_match_parse(new_adv_ids[:20])
        print("Waiting 15s for parsing...")
        time.sleep(15)

        print(f"Fetching advanced data for {len(new_adv_ids)} new matches...")
        adv_results = []
        for mid in new_adv_ids[:20]:
            try:
                adv = fetch_match_advanced_data(mid)
                if adv:
                    adv_results.append(adv)
                time.sleep(0.5)
            except Exception as e:
                print(f"  Error fetching advanced data for {mid}: {e}")
        if adv_results:
            save_match_advanced(adv_results)

    print("\nDone! Data saved to Notion")


def quick_update():
    """Fetch only recent matches (faster)."""
    print("Fetching recent matches...")
    matches = fetch_recent_matches()
    save_matches(matches)
    print("Done!")


def backfill_items(batch_size=20):
    """Fetch items for all matches that don't have item data yet."""
    import time

    # Load all match IDs from Notion
    matches = nc.query_matches()
    all_match_ids = [str(m["match_id"]) for m in matches]

    # Find matches without items
    existing_items = load_existing_items()
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
        save_match_items(items_data)
        total_fetched += len(items_data)

        print(f"Progress: {total_fetched}/{len(missing_ids)} matches processed")

        if i + batch_size < len(missing_ids):
            print("Waiting before next batch...")
            time.sleep(2)

    print(f"\nDone! Fetched items for {total_fetched} matches.")


def backfill_advanced_data(batch_size=20):
    """Fetch advanced data for all matches that don't have it yet."""
    import time

    # Load all match IDs from Notion
    matches = nc.query_matches()
    all_match_ids = [str(m["match_id"]) for m in matches]

    # Find matches without advanced data
    existing_advanced = load_existing_advanced_data()
    missing_ids = [mid for mid in all_match_ids if mid not in existing_advanced]

    if not missing_ids:
        print("All matches already have advanced data!")
        return

    print(f"Found {len(missing_ids)} matches without advanced data.")

    # Request OpenDota to parse matches first (needed for lane_role)
    print(f"Requesting OpenDota to parse {len(missing_ids)} matches...")
    requested = request_match_parse(missing_ids)
    print(f"Requested parsing for {requested} matches. Waiting 30s for parsing...")
    time.sleep(30)

    print(f"Fetching advanced data in batches of {batch_size}...")

    total_fetched = 0
    for i in range(0, len(missing_ids), batch_size):
        batch = missing_ids[i:i + batch_size]
        print(f"\nBatch {i // batch_size + 1}: Fetching advanced data for {len(batch)} matches...")

        batch_results = []
        for j, match_id in enumerate(batch):
            try:
                print(f"  Fetching match {j+1}/{len(batch)}: {match_id}")
                advanced_data = fetch_match_advanced_data(match_id)
                if advanced_data:
                    batch_results.append(advanced_data)
                    total_fetched += 1
                time.sleep(0.5)
            except Exception as e:
                print(f"  Error fetching match {match_id}: {e}")

        # Save batch to Notion
        save_match_advanced(batch_results)
        print(f"Progress: {total_fetched}/{len(missing_ids)} matches processed")

        if i + batch_size < len(missing_ids):
            print("Waiting before next batch...")
            time.sleep(2)

    print(f"\nDone! Fetched advanced data for {total_fetched} matches.")


def fetch_and_save_extra_data():
    """Fetch peers, totals, and hero matchups data and save to cache."""
    import json
    from pathlib import Path

    cache_dir = Path(__file__).parent / "cache"
    cache_dir.mkdir(exist_ok=True)

    # Fetch peers
    print("Fetching peers data...")
    peers = fetch_peers()
    with open(cache_dir / "peers.json", "w", encoding="utf-8") as f:
        json.dump(peers, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(peers)} peers to cache/peers.json")

    # Fetch totals
    print("\nFetching totals data...")
    totals = fetch_totals()
    with open(cache_dir / "totals.json", "w", encoding="utf-8") as f:
        json.dump(totals, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(totals)} totals to cache/totals.json")

    # Fetch hero matchups for frequently played heroes (games >= 5)
    print("\nFetching hero stats to identify frequently played heroes...")
    hero_stats = fetch_hero_stats()
    frequent_heroes = [h for h in hero_stats if h.get("games", 0) >= 5]

    print(f"Found {len(frequent_heroes)} heroes with >= 5 games")
    print("Fetching hero matchups...")

    matchups = {}
    # Load existing matchups to support incremental fetching
    matchups_file = cache_dir / "hero_matchups.json"
    if matchups_file.exists():
        try:
            with open(matchups_file, "r", encoding="utf-8") as f:
                matchups = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    import time
    for i, hero in enumerate(frequent_heroes):
        hero_id = hero.get("hero_id")
        hero_name = HEROES_CN.get(hero_id, "Unknown")
        if str(hero_id) in matchups:
            print(f"  [{i+1}/{len(frequent_heroes)}] Skipping {hero_name} (already cached)")
            continue
        try:
            print(f"  [{i+1}/{len(frequent_heroes)}] Fetching matchups for {hero_name} (ID: {hero_id})...")
            matchup_data = fetch_hero_matchups(hero_id)
            matchups[str(hero_id)] = {
                "hero_id": hero_id,
                "hero_name": HEROES_EN.get(hero_id, "unknown"),
                "hero_cn": hero_name,
                "matchups": matchup_data
            }
            # Save incrementally after each hero
            with open(matchups_file, "w", encoding="utf-8") as f:
                json.dump(matchups, f, ensure_ascii=False, indent=2)
            time.sleep(0.5)  # Rate limiting
        except Exception as e:
            print(f"    Error fetching matchups for {hero_name}: {e}")
            # Save what we have so far
            with open(matchups_file, "w", encoding="utf-8") as f:
                json.dump(matchups, f, ensure_ascii=False, indent=2)

    with open(cache_dir / "hero_matchups.json", "w", encoding="utf-8") as f:
        json.dump(matchups, f, ensure_ascii=False, indent=2)
    print(f"\nSaved matchups for {len(matchups)} heroes to cache/hero_matchups.json")

    print("\nDone! All extra data saved to cache/")


def backfill_roles(batch_size=20, force=False):
    """Compute lane+farm based roles for matches.

    Args:
        batch_size: number of matches per batch
        force: if True, recompute all matches (not just missing)
    """
    import time

    matches = nc.query_matches()
    if force:
        targets = matches
    else:
        targets = [m for m in matches if m.get("role", 0) == 0]

    if not targets:
        print("All matches already have role data!")
        return

    print(f"Found {len(targets)} matches to process (force={force}).")
    print(f"Fetching match details in batches of {batch_size}...")

    total_updated = 0
    for i in range(0, len(targets), batch_size):
        batch = targets[i:i + batch_size]
        print(f"\nBatch {i // batch_size + 1}: Processing {len(batch)} matches...")

        for j, m in enumerate(batch):
            mid = str(m["match_id"])
            try:
                print(f"  Fetching match {j+1}/{len(batch)}: {mid}")
                details = fetch_match_details(mid)
                all_players = details.get("players", [])

                # Find player and their team
                player_data = None
                player_team = None
                for p in all_players:
                    if p.get("account_id") == STEAM_ID:
                        player_data = p
                        player_team = p.get("player_slot", 0) < 128
                        break

                if not player_data:
                    print(f"    Player not found in match {mid}")
                    continue

                # Compute role using lane + farm priority
                teammates = [p for p in all_players if (p.get("player_slot", 0) < 128) == player_team]
                role = compute_role(STEAM_ID, teammates)

                if role > 0:
                    nc.update_match_role(mid, role)
                    total_updated += 1
                    print(f"    Set role = Pos {role}")

                time.sleep(0.5)
            except Exception as e:
                print(f"    Error processing match {mid}: {e}")

        print(f"Progress: {total_updated}/{len(targets)} matches updated")

        if i + batch_size < len(targets):
            print("Waiting before next batch...")
            time.sleep(2)

    print(f"\nDone! Updated roles for {total_updated} matches.")


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
    elif len(sys.argv) > 1 and sys.argv[1] == "--advanced":
        # Backfill advanced data for all matches: python fetch_dota_stats.py --advanced
        backfill_advanced_data()
    elif len(sys.argv) > 1 and sys.argv[1] == "--fix-roles":
        # Backfill lane+farm based roles: python fetch_dota_stats.py --fix-roles [--force]
        force = "--force" in sys.argv
        backfill_roles(force=force)
    elif len(sys.argv) > 1 and sys.argv[1] == "--calibrate":
        # Calibrate MMR to actual value: python fetch_dota_stats.py --calibrate 3900
        if len(sys.argv) > 2:
            try:
                mmr = int(sys.argv[2])
                nc.update_profile({"current_mmr": mmr, "estimated_mmr": mmr})
                update_mmr_history(mmr, "Calibrate")
                print(f"MMR calibrated to {mmr}")
            except ValueError:
                print("Invalid MMR value")
        else:
            print("Usage: python fetch_dota_stats.py --calibrate <mmr_value>")
    elif len(sys.argv) > 1 and sys.argv[1] == "--extra":
        # Fetch extra data (peers, totals, matchups): python fetch_dota_stats.py --extra
        fetch_and_save_extra_data()
    else:
        limit = 500
        if len(sys.argv) > 1:
            try:
                limit = int(sys.argv[1])
            except ValueError:
                pass
        update_all(match_limit=limit)
