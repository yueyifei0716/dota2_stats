"""Data reading layer — wraps notion_db + notion_cache."""

import json
from pathlib import Path

import notion_db as nc
import notion_cache as cache

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def read_matches():
    cached = cache.get("matches")
    if cached is not None:
        return cached
    try:
        matches = nc.query_matches()
        cache.set("matches", matches)
        return matches
    except Exception as e:
        print(f"Notion error (matches): {e}")
        return cache.get_stale("matches") or []


def read_profile():
    cached = cache.get("profile")
    if cached is not None:
        return cached
    try:
        profile = nc.get_profile()
        cache.set("profile", profile)
        return profile
    except Exception as e:
        print(f"Notion error (profile): {e}")
        return cache.get_stale("profile") or {}


def read_hero_stats():
    cached = cache.get("hero_stats")
    if cached is not None:
        return cached
    try:
        stats = nc.query_hero_stats()
        cache.set("hero_stats", stats)
        return stats
    except Exception as e:
        print(f"Notion error (hero_stats): {e}")
        return cache.get_stale("hero_stats") or []


def read_mmr_history():
    cached = cache.get("mmr_history")
    if cached is not None:
        return cached
    try:
        history = nc.query_mmr_history()
        cache.set("mmr_history", history)
        return history
    except Exception as e:
        print(f"Notion error (mmr_history): {e}")
        return cache.get_stale("mmr_history") or []


def fetch_player_ratings():
    """Fetch rank tier history from OpenDota API (cached)."""
    import requests
    cached = cache.get("ratings")
    if cached is not None:
        return cached
    try:
        url = "https://api.opendota.com/api/players/894447460/ratings"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        cache.set("ratings", data)
        return data
    except Exception as e:
        print(f"OpenDota ratings error: {e}")
        return cache.get_stale("ratings") or []


def read_peers_cache():
    cache_file = PROJECT_ROOT / "cache" / "peers.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                peers = json.load(f)
            peers = [p for p in peers if p.get("with_games", 0) >= 3]
            peers.sort(key=lambda x: -x.get("with_games", 0))
            return peers[:10]
        except (json.JSONDecodeError, IOError):
            pass
    return []


def read_hero_matchups_cache():
    cache_file = PROJECT_ROOT / "cache" / "hero_matchups.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}
