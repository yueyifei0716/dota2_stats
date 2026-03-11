"""GET /api/dashboard — aggregated dashboard data."""

from collections import defaultdict
from fastapi import APIRouter

from services.cache import read_matches, read_profile, read_hero_stats, read_mmr_history, fetch_player_ratings, read_peers_cache, read_hero_matchups_cache
from services.stats import (
    get_rank_name, get_rank_name_simple, calculate_impact_score, enrich_match,
    calc_rolling_winrate, calc_time_analysis, calc_recent_trend, calc_streak,
    calc_role_performance, HEROES_CN,
)
from fetch_dota_stats import fetch_player_rankings

router = APIRouter()


@router.get("/dashboard")
def dashboard():
    profile = read_profile()
    matches = read_matches()
    hero_stats = read_hero_stats()
    mmr_history = read_mmr_history()

    # Enrich all matches
    for m in matches:
        enrich_match(m)

    # Stats overview
    recent = matches[:20]
    recent_wins = sum(1 for m in recent if m.get("win") == "Win")
    recent_losses = len(recent) - recent_wins
    streak_count, streak_label = calc_streak(matches)

    # Hero frequency in recent games
    hero_freq = defaultdict(lambda: {"count": 0, "icon": "", "name": ""})
    for m in recent:
        hero_cn = m.get("hero_cn", "未知")
        hero_freq[hero_cn]["count"] += 1
        hero_freq[hero_cn]["icon"] = m.get("hero_icon", "")
        hero_freq[hero_cn]["name"] = hero_cn
    most_played_recent = sorted(hero_freq.values(), key=lambda x: -x["count"])[:5]

    # Hero stats
    hero_stats_sorted = sorted(hero_stats, key=lambda x: -int(x.get("games", 0)))[:15]
    qualified = [h for h in hero_stats if int(h.get("games", 0)) >= 10]
    best_heroes = sorted(qualified, key=lambda x: -float(x.get("win_rate", 0)))[:5]
    worst_heroes = sorted(qualified, key=lambda x: float(x.get("win_rate", 0)))[:5]

    # Unique heroes for filter
    all_heroes = sorted(set((m.get("hero_cn", ""), m.get("hero_icon", "")) for m in matches), key=lambda x: x[0])

    # MMR chart data
    mmr_dates = [h.get("date", "")[:10] for h in mmr_history]
    mmr_values = [int(h.get("mmr", 0)) for h in mmr_history]

    # Rank history
    ratings = fetch_player_ratings()
    rank_history = [{"date": r.get("time", "")[:10], "tier": r.get("rank_tier", 0), "label": get_rank_name_simple(r.get("rank_tier", 0))} for r in ratings]

    # Rankings
    hero_id_to_name = {}
    hero_id_to_icon = {}
    for h in hero_stats:
        hid = h.get("hero_id")
        if hid:
            hero_id_to_name[int(hid)] = h.get("hero_cn", "未知")
            hero_id_to_icon[int(hid)] = h.get("hero_icon", "")

    rankings = fetch_player_rankings()
    top_rankings = []
    for r in rankings[:10]:
        hid = r.get("hero_id")
        pct = r.get("percent_rank", 0) * 100
        top_rankings.append({"hero_id": hid, "hero_cn": hero_id_to_name.get(hid, f"英雄 {hid}"), "hero_icon": hero_id_to_icon.get(hid, ""), "percent_rank": pct, "top_percent": 100 - pct})

    # Role performance
    role_performance = calc_role_performance(matches)

    # Charts
    rolling_winrate = calc_rolling_winrate(matches)
    time_analysis, weekday_analysis = calc_time_analysis(matches)
    recent_trend = calc_recent_trend(matches)

    # Peers
    peers = read_peers_cache()

    # Hero matchups dropdown
    matchups_raw = read_hero_matchups_cache()
    matchup_heroes = sorted([{"hero_id": int(hid), "hero_cn": data.get("hero_cn", ""), "hero_en": data.get("hero_name", "")} for hid, data in matchups_raw.items()], key=lambda x: x["hero_cn"])

    rank_name, rank_icon = get_rank_name(profile.get("rank_tier"))

    return {
        "profile": {**profile, "rank_name": rank_name, "rank_icon": rank_icon},
        "stats": {
            "recent_wins": recent_wins,
            "recent_losses": recent_losses,
            "streak_count": streak_count,
            "streak_label": streak_label,
            "most_played_recent": most_played_recent,
        },
        "hero_stats": hero_stats_sorted,
        "best_heroes": best_heroes,
        "worst_heroes": worst_heroes,
        "all_heroes": [{"name": h[0], "icon": h[1]} for h in all_heroes],
        "mmr": {"dates": mmr_dates, "values": mmr_values},
        "rank_history": rank_history,
        "top_rankings": top_rankings,
        "role_performance": role_performance,
        "rolling_winrate": rolling_winrate,
        "time_analysis": time_analysis,
        "weekday_analysis": weekday_analysis,
        "recent_trend": recent_trend,
        "peers": peers,
        "matchup_heroes": matchup_heroes,
    }
