"""
Notion API wrapper for Dota 2 Stats Tracker.
Handles all CRUD operations against Notion databases.
"""

import os
import time
import json
from datetime import datetime
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
MATCHES_DB_ID = os.getenv("NOTION_MATCHES_DB_ID")
HERO_STATS_DB_ID = os.getenv("NOTION_HERO_STATS_DB_ID")
MMR_HISTORY_DB_ID = os.getenv("NOTION_MMR_HISTORY_DB_ID")
PROFILE_DB_ID = os.getenv("NOTION_PROFILE_DB_ID")
MATCHES_DB_ID = os.getenv("NOTION_MATCHES_DB_ID")
HERO_STATS_DB_ID = os.getenv("NOTION_HERO_STATS_DB_ID")
MMR_HISTORY_DB_ID = os.getenv("NOTION_MMR_HISTORY_DB_ID")
PROFILE_DB_ID = os.getenv("NOTION_PROFILE_DB_ID")

notion = Client(auth=NOTION_TOKEN)

# Rate limiting: max 3 requests per second
_last_request_time = 0
_MIN_INTERVAL = 0.34  # ~3 req/s


def _rate_limit():
    """Enforce rate limiting between API calls."""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_request_time = time.time()


def _retry(func, max_retries=3):
    """Retry with exponential backoff."""
    for attempt in range(max_retries):
        try:
            _rate_limit()
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            print(f"  Retry {attempt + 1}/{max_retries} after {wait}s: {e}")
            time.sleep(wait)


# --- Property builders ---

def _title(value):
    return {"title": [{"text": {"content": str(value) if value else ""}}]}


def _rich_text(value):
    return {"rich_text": [{"text": {"content": str(value) if value else ""}}]}


def _number(value):
    if value is None or value == "":
        return {"number": None}
    try:
        return {"number": float(value)}
    except (ValueError, TypeError):
        return {"number": None}


def _checkbox(value):
    if isinstance(value, str):
        return {"checkbox": value.lower() in ("true", "1", "yes")}
    return {"checkbox": bool(value)}


def _date(value):
    if not value:
        return {"date": None}
    return {"date": {"start": str(value)}}


def _url(value):
    if not value:
        return {"url": None}
    return {"url": str(value)}


def _select(value):
    if not value:
        return {"select": None}
    return {"select": {"name": str(value)}}


# --- Property extractors (read from Notion page) ---

def _get_title(props, key):
    try:
        return props[key]["title"][0]["text"]["content"]
    except (KeyError, IndexError, TypeError):
        return ""


def _get_text(props, key):
    try:
        return props[key]["rich_text"][0]["text"]["content"]
    except (KeyError, IndexError, TypeError):
        return ""


def _get_number(props, key):
    try:
        val = props[key]["number"]
        return val if val is not None else 0
    except (KeyError, TypeError):
        return 0


def _get_checkbox(props, key):
    try:
        return props[key]["checkbox"]
    except (KeyError, TypeError):
        return False


def _get_date(props, key):
    try:
        return props[key]["date"]["start"]
    except (KeyError, TypeError):
        return ""


def _get_url(props, key):
    try:
        return props[key]["url"] or ""
    except (KeyError, TypeError):
        return ""


def _get_select(props, key):
    try:
        return props[key]["select"]["name"]
    except (KeyError, TypeError):
        return ""


# --- Match helpers ---

def _build_match_properties(match_data):
    """Build Notion properties dict from a match data dict."""
    props = {
        "Match ID": _title(match_data.get("match_id", "")),
        "Timestamp": _number(match_data.get("timestamp")),
        "Hero": _rich_text(match_data.get("hero", "")),
        "Hero CN": _rich_text(match_data.get("hero_cn", "")),
        "Hero ID": _number(match_data.get("hero_id")),
        "Hero Icon": _url(match_data.get("hero_icon", "")),
        "Win": _checkbox(match_data.get("win", "") == "Win" if isinstance(match_data.get("win"), str) else match_data.get("win", False)),
        "Kills": _number(match_data.get("kills")),
        "Deaths": _number(match_data.get("deaths")),
        "Assists": _number(match_data.get("assists")),
        "KDA": _number(match_data.get("kda")),
        "Last Hits": _number(match_data.get("last_hits")),
        "GPM": _number(match_data.get("gpm")),
        "XPM": _number(match_data.get("xpm")),
        "Hero Damage": _number(match_data.get("hero_damage")),
        "Tower Damage": _number(match_data.get("tower_damage")),
        "Hero Healing": _number(match_data.get("hero_healing")),
        "Duration": _rich_text(match_data.get("duration", "")),
        "Game Mode": _select(match_data.get("game_mode", "")),
        "Lobby Type": _select(match_data.get("lobby_type", "")),
        "Party Size": _number(match_data.get("party_size")),
        "Avg Rank": _number(match_data.get("avg_rank")),
    }
    # Lane role from basic match data
    if match_data.get("lane_role"):
        props["Lane Role"] = _number(match_data.get("lane_role"))
    # Date field
    date_str = match_data.get("date", "")
    if date_str:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            props["Date"] = _date(dt.isoformat())
        except ValueError:
            props["Date"] = _date(date_str)
    return props


def _build_advanced_properties(adv):
    """Build Notion properties for advanced match fields."""
    return {
        "Lane Role": _number(adv.get("lane_role")),
        "Role": _number(adv.get("role")),
        "Lane": _number(adv.get("lane")),
        "Is Roaming": _checkbox(adv.get("is_roaming", False)),
        "Net Worth": _number(adv.get("net_worth")),
        "Level": _number(adv.get("level")),
        "Gold Spent": _number(adv.get("gold_spent")),
        "Adv Hero Damage": _number(adv.get("hero_damage")),
        "Adv Tower Damage": _number(adv.get("tower_damage")),
        "Adv Kills": _number(adv.get("kills")),
        "Adv Deaths": _number(adv.get("deaths")),
        "Adv Assists": _number(adv.get("assists")),
        "Max Gold Lead": _number(adv.get("max_gold_lead")),
        "Max Gold Deficit": _number(adv.get("max_gold_deficit")),
        "Is Comeback": _checkbox(adv.get("is_comeback", False)),
        "Is Throw": _checkbox(adv.get("is_throw", False)),
        "Benchmark GPM Pct": _number(adv.get("benchmark_gpm_pct")),
        "Benchmark XPM Pct": _number(adv.get("benchmark_xpm_pct")),
        "Benchmark Kills Pct": _number(adv.get("benchmark_kills_pct")),
        "Benchmark Damage Pct": _number(adv.get("benchmark_damage_pct")),
        "Benchmark Tower Pct": _number(adv.get("benchmark_tower_pct")),
        "Ally Heroes": _rich_text(adv.get("ally_heroes", "")),
        "Enemy Heroes": _rich_text(adv.get("enemy_heroes", "")),
    }


def _build_item_properties(items_data):
    """Build Notion properties for item fields."""
    items = items_data.get("items", [0, 0, 0, 0, 0, 0])
    props = {}
    for i in range(6):
        val = items[i] if i < len(items) else 0
        props[f"Item {i}"] = _number(val)
    props["Item Neutral"] = _number(items_data.get("item_neutral", 0))
    return props


def _page_to_match(page):
    """Extract a match dict from a Notion page."""
    p = page["properties"]
    return {
        "page_id": page["id"],
        "match_id": _get_title(p, "Match ID"),
        "date": _get_date(p, "Date"),
        "timestamp": _get_number(p, "Timestamp"),
        "hero": _get_text(p, "Hero"),
        "hero_cn": _get_text(p, "Hero CN"),
        "hero_id": int(_get_number(p, "Hero ID")),
        "hero_icon": _get_url(p, "Hero Icon"),
        "win": "Win" if _get_checkbox(p, "Win") else "Loss",
        "kills": int(_get_number(p, "Kills")),
        "deaths": int(_get_number(p, "Deaths")),
        "assists": int(_get_number(p, "Assists")),
        "kda": _get_number(p, "KDA"),
        "last_hits": int(_get_number(p, "Last Hits")),
        "gpm": int(_get_number(p, "GPM")),
        "xpm": int(_get_number(p, "XPM")),
        "hero_damage": int(_get_number(p, "Hero Damage")),
        "tower_damage": int(_get_number(p, "Tower Damage")),
        "hero_healing": int(_get_number(p, "Hero Healing")),
        "duration": _get_text(p, "Duration"),
        "game_mode": _get_select(p, "Game Mode"),
        "lobby_type": _get_select(p, "Lobby Type"),
        "party_size": _get_number(p, "Party Size"),
        "avg_rank": _get_number(p, "Avg Rank"),
        # Advanced fields
        "lane_role": int(_get_number(p, "Lane Role")),
        "role": int(_get_number(p, "Role")),
        "lane": int(_get_number(p, "Lane")),
        "is_roaming": _get_checkbox(p, "Is Roaming"),
        "net_worth": int(_get_number(p, "Net Worth")),
        "level": int(_get_number(p, "Level")),
        "gold_spent": int(_get_number(p, "Gold Spent")),
        "adv_hero_damage": int(_get_number(p, "Adv Hero Damage")),
        "adv_tower_damage": int(_get_number(p, "Adv Tower Damage")),
        "adv_kills": int(_get_number(p, "Adv Kills")),
        "adv_deaths": int(_get_number(p, "Adv Deaths")),
        "adv_assists": int(_get_number(p, "Adv Assists")),
        "max_gold_lead": int(_get_number(p, "Max Gold Lead")),
        "max_gold_deficit": int(_get_number(p, "Max Gold Deficit")),
        "is_comeback": _get_checkbox(p, "Is Comeback"),
        "is_throw": _get_checkbox(p, "Is Throw"),
        "benchmark_gpm_pct": _get_number(p, "Benchmark GPM Pct"),
        "benchmark_xpm_pct": _get_number(p, "Benchmark XPM Pct"),
        "benchmark_kills_pct": _get_number(p, "Benchmark Kills Pct"),
        "benchmark_damage_pct": _get_number(p, "Benchmark Damage Pct"),
        "benchmark_tower_pct": _get_number(p, "Benchmark Tower Pct"),
        "ally_heroes": _get_text(p, "Ally Heroes"),
        "enemy_heroes": _get_text(p, "Enemy Heroes"),
        # Items
        "item_0": int(_get_number(p, "Item 0")),
        "item_1": int(_get_number(p, "Item 1")),
        "item_2": int(_get_number(p, "Item 2")),
        "item_3": int(_get_number(p, "Item 3")),
        "item_4": int(_get_number(p, "Item 4")),
        "item_5": int(_get_number(p, "Item 5")),
        "item_neutral": int(_get_number(p, "Item Neutral")),
        # Notes
        "note": _get_text(p, "Note"),
        "note_updated_at": _get_text(p, "Note Updated At"),
    }


# --- Query helpers ---

def _query_all_pages(database_id, sorts=None, filter_obj=None):
    """Query all pages from a database, handling pagination."""
    pages = []
    start_cursor = None
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    while True:
        payload = {"page_size": 100}
        if sorts:
            payload["sorts"] = sorts
        if filter_obj:
            payload["filter"] = filter_obj
        if start_cursor:
            payload["start_cursor"] = start_cursor
        
        import requests
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        pages.extend(result["results"])
        if not result.get("has_more"):
            break
        start_cursor = result.get("next_cursor")
    return pages


# --- Matches CRUD ---

def query_matches():
    """Query all matches, sorted by timestamp descending (newest first)."""
    pages = _query_all_pages(
        MATCHES_DB_ID,
        sorts=[{"property": "Timestamp", "direction": "descending"}]
    )
    return [_page_to_match(p) for p in pages]


def get_existing_match_ids():
    """Get set of match IDs already in Notion (fast, title-only query)."""
    pages = _query_all_pages(MATCHES_DB_ID)
    ids = set()
    for p in pages:
        mid = _get_title(p["properties"], "Match ID")
        if mid:
            ids.add(mid)
    return ids


def find_match_page_id(match_id):
    """Find the Notion page ID for a given match_id."""
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    import requests
    url = f"https://api.notion.com/v1/databases/{MATCHES_DB_ID}/query"
    payload = {"filter": {"property": "Match ID", "title": {"equals": str(match_id)}}}
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        result = response.json()
        if result["results"]:
            return result["results"][0]["id"]
    return None


def create_match(match_data):
    """Create a new match page in Notion."""
    props = _build_match_properties(match_data)
    return _retry(lambda: notion.pages.create(
        parent={"database_id": MATCHES_DB_ID},
        properties=props
    ))


def update_match(page_id, properties):
    """Update an existing match page with additional properties."""
    return _retry(lambda: notion.pages.update(
        page_id=page_id,
        properties=properties
    ))


def update_match_items(match_id, items_data):
    """Update item properties on an existing match page."""
    page_id = find_match_page_id(match_id)
    if not page_id:
        print(f"  Match {match_id} not found in Notion, skipping items")
        return None
    props = _build_item_properties(items_data)
    return update_match(page_id, props)


def update_match_advanced(match_id, adv_data):
    """Update advanced properties on an existing match page."""
    page_id = find_match_page_id(match_id)
    if not page_id:
        print(f"  Match {match_id} not found in Notion, skipping advanced")
        return None
    props = _build_advanced_properties(adv_data)
    return update_match(page_id, props)


def update_match_note(match_id, note):
    """Update the note on a match page."""
    page_id = find_match_page_id(match_id)
    if not page_id:
        return None
    props = {
        "Note": _rich_text(note),
        "Note Updated At": _rich_text(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    }
    return update_match(page_id, props)


def update_match_role(match_id, role):
    """Update the Role field on a match page."""
    page_id = find_match_page_id(match_id)
    if not page_id:
        print(f"  Match {match_id} not found in Notion, skipping role update")
        return None
    return update_match(page_id, {"Role": _number(role)})


# --- Hero Stats CRUD ---

def _page_to_hero_stat(page):
    p = page["properties"]
    return {
        "page_id": page["id"],
        "hero_cn": _get_title(p, "Hero CN"),
        "hero": _get_text(p, "Hero"),
        "hero_id": int(_get_number(p, "Hero ID")),
        "hero_icon": _get_url(p, "Hero Icon"),
        "games": int(_get_number(p, "Games")),
        "wins": int(_get_number(p, "Wins")),
        "win_rate": _get_number(p, "Win Rate"),
    }


def query_hero_stats():
    """Query all hero stats."""
    pages = _query_all_pages(HERO_STATS_DB_ID)
    return [_page_to_hero_stat(p) for p in pages]


def upsert_hero_stat(hero_data):
    """Create or update a hero stat row by Hero ID."""
    hero_id = hero_data.get("hero_id")
    # Search for existing
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    import requests
    url = f"https://api.notion.com/v1/databases/{HERO_STATS_DB_ID}/query"
    payload = {"filter": {"property": "Hero ID", "number": {"equals": int(hero_id)}}}
    response = requests.post(url, headers=headers, json=payload)
    result = response.json() if response.status_code == 200 else {"results": []}
    props = {
        "Hero CN": _title(hero_data.get("hero_cn", "")),
        "Hero": _rich_text(hero_data.get("hero", "")),
        "Hero ID": _number(hero_id),
        "Hero Icon": _url(hero_data.get("hero_icon", "")),
        "Games": _number(hero_data.get("games")),
        "Wins": _number(hero_data.get("wins")),
        "Win Rate": _number(hero_data.get("win_rate")),
    }
    if result["results"]:
        page_id = result["results"][0]["id"]
        return _retry(lambda: notion.pages.update(page_id=page_id, properties=props))
    else:
        return _retry(lambda: notion.pages.create(
            parent={"database_id": HERO_STATS_DB_ID}, properties=props
        ))


# --- MMR History CRUD ---

def _page_to_mmr_entry(page):
    p = page["properties"]
    return {
        "date": _get_title(p, "Date"),
        "mmr": int(_get_number(p, "MMR")),
        "result": _get_select(p, "Result"),
    }


def query_mmr_history():
    """Query all MMR history entries, sorted by date ascending."""
    pages = _query_all_pages(MMR_HISTORY_DB_ID)
    entries = [_page_to_mmr_entry(p) for p in pages]
    # Sort by date ascending for chronological chart display
    entries.sort(key=lambda x: x.get("date", ""))
    return entries


def append_mmr_history(mmr, result=""):
    """Add a new MMR history entry."""
    props = {
        "Date": _title(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "MMR": _number(mmr),
    }
    if result:
        props["Result"] = _select(result)
    return _retry(lambda: notion.pages.create(
        parent={"database_id": MMR_HISTORY_DB_ID}, properties=props
    ))


# --- Profile CRUD ---

def _page_to_profile(page):
    p = page["properties"]
    return {
        "page_id": page["id"],
        "username": _get_title(p, "Username"),
        "steam_id": int(_get_number(p, "Steam ID")),
        "rank_tier": int(_get_number(p, "Rank Tier")),
        "current_mmr": int(_get_number(p, "Current MMR")),
        "estimated_mmr": int(_get_number(p, "Estimated MMR")),
        "country": _get_text(p, "Country"),
        "total_wins": int(_get_number(p, "Total Wins")),
        "total_losses": int(_get_number(p, "Total Losses")),
        "win_rate": _get_number(p, "Win Rate"),
        "last_updated": _get_text(p, "Last Updated"),
    }


def get_profile():
    """Get the single profile row."""
    pages = _query_all_pages(PROFILE_DB_ID)
    if pages:
        return _page_to_profile(pages[0])
    return {}


def update_profile(profile_data):
    """Create or update the single profile row."""
    pages = _query_all_pages(PROFILE_DB_ID)
    props = {
        "Username": _title(profile_data.get("username", "")),
        "Steam ID": _number(profile_data.get("steam_id")),
        "Rank Tier": _number(profile_data.get("rank_tier")),
        "Current MMR": _number(profile_data.get("current_mmr")),
        "Estimated MMR": _number(profile_data.get("estimated_mmr")),
        "Country": _rich_text(profile_data.get("country", "")),
        "Total Wins": _number(profile_data.get("total_wins")),
        "Total Losses": _number(profile_data.get("total_losses")),
        "Win Rate": _number(profile_data.get("win_rate")),
        "Last Updated": _rich_text(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ),
    }
    if pages:
        page_id = pages[0]["id"]
        return _retry(lambda: notion.pages.update(page_id=page_id, properties=props))
    else:
        return _retry(lambda: notion.pages.create(
            parent={"database_id": PROFILE_DB_ID}, properties=props
        ))

# Compatibility aliases for app.py
read_profile = get_profile
read_matches = query_matches
read_hero_stats = query_hero_stats
read_mmr_history = query_mmr_history
