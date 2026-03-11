"""Hero-related API endpoints."""

from fastapi import APIRouter

from services.cache import read_hero_stats, read_hero_matchups_cache
from fetch_dota_stats import HEROES_CN, HEROES_EN, get_hero_icon_url

router = APIRouter()


@router.get("/heroes")
def get_heroes():
    return read_hero_stats()


@router.get("/all_heroes")
def get_all_heroes():
    """Return all 127 Dota 2 heroes (not just played ones)."""
    heroes = []
    for hero_id, cn_name in HEROES_CN.items():
        heroes.append({
            "hero_id": hero_id,
            "hero_cn": cn_name,
            "hero_en": HEROES_EN.get(hero_id, ""),
            "hero_icon": get_hero_icon_url(hero_id),
        })
    return sorted(heroes, key=lambda x: x["hero_cn"])


@router.get("/hero_matchups/{hero_id}")
def get_hero_matchups(hero_id: int):
    matchups = read_hero_matchups_cache()
    data = matchups.get(str(hero_id), {})
    if not data:
        return {"best": [], "worst": []}

    raw = data.get("matchups", [])
    filtered = [m for m in raw if m.get("games_played", 0) >= 10]

    processed = []
    for m in filtered:
        games = m["games_played"]
        wins = m.get("wins", 0)
        wr = round(wins / games * 100, 1) if games else 0
        processed.append({
            "hero_id": m.get("hero_id"),
            "hero_cn": HEROES_CN.get(m.get("hero_id"), f"英雄 {m.get('hero_id')}"),
            "games": games, "wins": wins, "winrate": wr,
        })

    best = sorted(processed, key=lambda x: -x["winrate"])[:5]
    worst = sorted(processed, key=lambda x: x["winrate"])[:5]
    return {"best": best, "worst": worst}
