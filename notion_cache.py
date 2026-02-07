"""
Caching layer for Notion API responses.
In-memory cache with TTL + file-based fallback for persistence.
"""

import json
import time
from pathlib import Path

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_TTL = 300  # 5 minutes

_memory_cache = {}


def _ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get(key):
    """Get cached data. Returns None if expired or missing."""
    if key in _memory_cache:
        entry = _memory_cache[key]
        if time.time() - entry["time"] < CACHE_TTL:
            return entry["data"]
        del _memory_cache[key]

    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                entry = json.load(f)
            if time.time() - entry["time"] < CACHE_TTL:
                _memory_cache[key] = entry
                return entry["data"]
        except (json.JSONDecodeError, KeyError):
            pass
    return None


def set(key, data):
    """Store data in both memory and file cache."""
    entry = {"time": time.time(), "data": data}
    _memory_cache[key] = entry
    _ensure_cache_dir()
    try:
        cache_file = CACHE_DIR / f"{key}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False)
    except Exception:
        pass


def get_stale(key):
    """Get cached data even if expired (fallback when Notion is down)."""
    if key in _memory_cache:
        return _memory_cache[key]["data"]
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)["data"]
        except (json.JSONDecodeError, KeyError):
            pass
    return None


def invalidate(key=None):
    """Invalidate cache. If key is None, invalidate all."""
    global _memory_cache
    if key:
        _memory_cache.pop(key, None)
        cache_file = CACHE_DIR / f"{key}.json"
        if cache_file.exists():
            cache_file.unlink()
    else:
        _memory_cache = {}
        if CACHE_DIR.exists():
            for f in CACHE_DIR.glob("*.json"):
                f.unlink()
