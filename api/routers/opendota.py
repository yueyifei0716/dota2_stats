"""OpenDota API proxy endpoints — wardmap, histograms, counts, item popularity, hero durations, pro encounters."""

import time
from typing import Optional

import requests
from fastapi import APIRouter

router = APIRouter()

STEAM_ID = 894447460
BASE_URL = "https://api.opendota.com/api"

# Simple in-memory cache for OpenDota proxy calls (10 min TTL)
_opendota_cache: dict = {}
_opendota_cache_ts: dict = {}
CACHE_TTL = 600  # 10 minutes


def _cached_get(key: str, url: str, params: dict | None = None, timeout: int = 15):
    """GET with simple in-memory caching."""
    now = time.time()
    if key in _opendota_cache and (now - _opendota_cache_ts.get(key, 0)) < CACHE_TTL:
        return _opendota_cache[key]
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        _opendota_cache[key] = data
        _opendota_cache_ts[key] = now
        return data
    except Exception as e:
        print(f"OpenDota API error ({key}): {e}")
        # Return stale cache if available
        if key in _opendota_cache:
            return _opendota_cache[key]
        return None


# ── 1. Ward Map ──

def _normalize_ward_data(raw: dict) -> list:
    """Convert wardmap data to [{x, y, count}] with coords normalized to 0-1.

    OpenDota wardmap format: {x_game: {y_game: count}}
    gameCoordToUV: x_screen = x_game - 64, y_screen = 127 - (y_game - 64)
    Screen coords are 0-127, normalize to 0-1.
    """
    dots = []
    for x_game_str, col in raw.items():
        for y_game_str, count in col.items():
            x_screen = int(x_game_str) - 64
            y_screen = 127 - (int(y_game_str) - 64)
            dots.append({
                "x": round(x_screen / 127, 4),
                "y": round(y_screen / 127, 4),
                "count": count,
            })
    return dots


@router.get("/wardmap")
def get_wardmap():
    """Get ward placement data for the player, coordinates normalized to 0-1."""
    data = _cached_get(
        "wardmap",
        f"{BASE_URL}/players/{STEAM_ID}/wardmap",
    )
    if not data:
        return {"obs": [], "sen": []}
    return {
        "obs": _normalize_ward_data(data.get("obs", {})),
        "sen": _normalize_ward_data(data.get("sen", {})),
    }


# ── 2. Histograms ──

@router.get("/histograms/{field}")
def get_histogram(field: str):
    """Get histogram data for a stat field (e.g. kills, gpm, xpm, kda, duration)."""
    allowed_fields = ["kills", "deaths", "assists", "kda", "gold_per_min", "xp_per_min",
                       "actions_per_min", "hero_damage", "tower_damage", "duration",
                       "last_hits", "hero_healing"]
    if field not in allowed_fields:
        return {"error": f"Invalid field. Allowed: {allowed_fields}"}

    data = _cached_get(
        f"histogram_{field}",
        f"{BASE_URL}/players/{STEAM_ID}/histograms/{field}",
    )
    if not data:
        return {"buckets": []}

    # Filter out empty buckets and format
    buckets = [
        {"x": item.get("x", 0), "games": item.get("games", 0)}
        for item in data
        if item.get("games", 0) > 0
    ]
    return {"field": field, "buckets": buckets}


# ── 3. Counts ──

@router.get("/counts")
def get_counts():
    """Get game counts by category (game mode, lobby type, side, lane role, etc.)."""
    data = _cached_get(
        "counts",
        f"{BASE_URL}/players/{STEAM_ID}/counts",
    )
    if not data:
        return {}

    GAME_MODES = {
        "0": "Unknown", "1": "All Pick", "2": "Captain's Mode", "3": "Random Draft",
        "4": "Single Draft", "5": "All Random", "12": "Least Played", "16": "Captain's Draft",
        "22": "All Pick (Ranked)", "23": "Turbo",
    }
    LOBBY_TYPES = {
        "0": "Normal", "1": "Practice", "2": "Tournament", "5": "Ranked",
        "7": "Bot", "9": "Battle Cup",
    }

    def format_counts(raw: dict, name_map: dict | None = None):
        """Convert {id: {games, win}} to sorted list."""
        items = []
        for key, val in raw.items():
            games = val.get("games", 0)
            wins = val.get("win", 0)
            if games == 0:
                continue
            label = name_map.get(key, key) if name_map else key
            items.append({
                "label": label,
                "games": games,
                "wins": wins,
                "winrate": round(wins / games * 100, 1) if games else 0,
            })
        return sorted(items, key=lambda x: -x["games"])

    result = {}
    if "game_mode" in data:
        result["game_mode"] = format_counts(data["game_mode"], GAME_MODES)
    if "lobby_type" in data:
        result["lobby_type"] = format_counts(data["lobby_type"], LOBBY_TYPES)
    if "is_radiant" in data:
        side_map = {"0": "夜魇 (Dire)", "1": "天辉 (Radiant)"}
        result["side"] = format_counts(data["is_radiant"], side_map)
    if "lane_role" in data:
        lane_map = {"1": "Safe Lane", "2": "Mid", "3": "Off Lane", "4": "Jungle"}
        result["lane_role"] = format_counts(data["lane_role"], lane_map)
    if "patch" in data:
        patches = format_counts(data["patch"])[:10]  # top 10 recent patches
        result["patch"] = patches

    return result


# ── 4. Hero Item Popularity ──

ROLE_NAMES = {1: "Pos 1", 2: "Pos 2", 3: "Pos 3", 4: "Pos 4", 5: "Pos 5"}


@router.get("/hero_items/{hero_id}")
def get_hero_items(hero_id: int):
    """Get popular items for a hero, split by role from player's match data + OpenDota global data."""
    from collections import defaultdict
    from services.cache import read_matches
    from services.stats import ITEM_NAMES, get_item_icon_url

    def make_item_entry(item_id: int, count: int):
        name = ITEM_NAMES.get(item_id, "")
        if not name:
            return None
        return {"item_id": item_id, "name": name, "icon": get_item_icon_url(item_id), "count": count}

    # ── Player's own data: items grouped by role ──
    matches = read_matches()
    role_items: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    role_games: dict[int, int] = defaultdict(int)

    for m in matches:
        if int(m.get("hero_id", 0)) != hero_id:
            continue
        role = m.get("role", 0) or m.get("lane_role", 0)
        if role not in ROLE_NAMES:
            continue
        role_games[role] += 1
        for i in range(6):
            item_id = m.get(f"item_{i}", 0)
            if item_id and int(item_id) > 0:
                role_items[role][int(item_id)] += 1
        neutral = m.get("item_neutral", 0)
        if neutral and int(neutral) > 0:
            role_items[role][int(neutral)] += 1

    by_role = []
    for role in sorted(role_games.keys()):
        items_sorted = sorted(role_items[role].items(), key=lambda x: -x[1])
        items_list = []
        for item_id, count in items_sorted[:12]:
            entry = make_item_entry(item_id, count)
            if entry:
                items_list.append(entry)
        by_role.append({
            "role": role,
            "role_name": ROLE_NAMES[role],
            "games": role_games[role],
            "items": items_list,
        })

    # ── OpenDota global data (not role-specific, as fallback/reference) ──
    global_data = _cached_get(
        f"hero_items_{hero_id}",
        f"{BASE_URL}/heroes/{hero_id}/itemPopularity",
    )

    def process_phase(phase_data: dict, top_n: int = 10) -> list:
        if not phase_data:
            return []
        items = []
        for item_id_str, count in phase_data.items():
            entry = make_item_entry(int(item_id_str), count) if item_id_str.isdigit() else None
            if entry:
                items.append(entry)
        return sorted(items, key=lambda x: -x["count"])[:top_n]

    global_items = {}
    if global_data:
        global_items = {
            "start_game": process_phase(global_data.get("start_game_items", {}), 8),
            "early_game": process_phase(global_data.get("early_game_items", {}), 10),
            "mid_game": process_phase(global_data.get("mid_game_items", {}), 10),
            "late_game": process_phase(global_data.get("late_game_items", {}), 10),
        }

    return {"by_role": by_role, "global": global_items}


# ── 5. Hero Durations ──

@router.get("/hero_durations/{hero_id}")
def get_hero_durations(hero_id: int):
    """Get win rate by game duration for a hero."""
    data = _cached_get(
        f"hero_durations_{hero_id}",
        f"{BASE_URL}/heroes/{hero_id}/durations",
    )
    if not data:
        return {"durations": []}

    durations = []
    for item in data:
        games = item.get("games_played", 0) or item.get("games", 0)
        wins = item.get("wins", 0)
        if games < 5:  # Skip statistically insignificant buckets
            continue
        raw_bin = item.get("duration_bin", 0)
        duration_min = int(raw_bin) // 60 if raw_bin else 0
        durations.append({
            "duration_min": duration_min,
            "label": f"{duration_min}min",
            "games": games,
            "wins": wins,
            "winrate": round(wins / games * 100, 1) if games else 0,
        })
    return {"durations": durations}


# ── 6. Pro Player Encounters ──

@router.get("/pro_encounters")
def get_pro_encounters():
    """Get matches played with/against professional players."""
    data = _cached_get(
        "pros",
        f"{BASE_URL}/players/{STEAM_ID}/pros",
    )
    if not data:
        return {"encounters": []}

    encounters = []
    for p in data:
        games = (p.get("with_games", 0) or 0) + (p.get("against_games", 0) or 0)
        if games == 0:
            continue
        with_games = p.get("with_games", 0) or 0
        with_wins = p.get("with_win", 0) or 0
        against_games = p.get("against_games", 0) or 0
        against_wins = p.get("against_win", 0) or 0
        encounters.append({
            "name": p.get("name") or p.get("personaname", "Unknown"),
            "team": p.get("team_name", ""),
            "avatar": p.get("avatarfull", ""),
            "with_games": with_games,
            "with_wins": with_wins,
            "against_games": against_games,
            "against_wins": against_wins,
            "total_games": games,
            "last_played": p.get("last_played"),
        })

    # Sort by total games, take top 20
    encounters.sort(key=lambda x: -x["total_games"])
    return {"encounters": encounters[:20]}
