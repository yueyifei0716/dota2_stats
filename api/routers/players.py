"""Player dashboard API backed by public OpenDota endpoints."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from datetime import datetime, timezone, timedelta
import json
import math
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from fastapi import APIRouter, Body, Header, HTTPException, Query

from fetch_dota_stats import HEROES_CN, HEROES_EN, get_hero_icon_url
from routers.commercial import verify_access_token
from services.stats import get_item_icon_url, get_rank_name, get_rank_name_simple

router = APIRouter()

BASE_URL = "https://api.opendota.com/api"
CACHE_TTL = 180
CN_TZ = timezone(timedelta(hours=8))
MATCH_DETAIL_LIMIT = 8

LANE_ROLE_NAMES = {
    0: "分路未解析",
    1: "优势路",
    2: "中路",
    3: "劣势路",
    4: "打野",
}

META_SCOPES = [
    {"key": "overall", "label": "All Public"},
]

GAME_MODES = {
    1: "All Pick",
    2: "Captain's Mode",
    3: "Random Draft",
    4: "Single Draft",
    5: "All Random",
    12: "Least Played",
    16: "Captain's Draft",
    22: "Ranked All Pick",
    23: "Turbo",
}

LOBBY_TYPES = {
    0: "Normal",
    1: "Practice",
    2: "Tournament",
    5: "Ranked",
    6: "Solo Ranked",
    7: "Ranked",
    9: "Battle Cup",
}

_cache: Dict[str, Dict[str, Any]] = {}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _round(value: float, digits: int = 1) -> float:
    return round(value, digits) if value == value else 0


def _signed(value: float, suffix: str = "") -> str:
    prefix = "+" if value > 0 else ""
    return f"{prefix}{value}{suffix}"


def _cached_get(path: str, params: Optional[Dict[str, Any]] = None, timeout: int = 12) -> Tuple[Any, Optional[str]]:
    params = dict(params or {})
    api_key = os.getenv("OPENDOTA_API_KEY")
    if api_key and "api_key" not in params:
        params["api_key"] = api_key

    cache_key = f"{path}:{sorted(params.items())}"
    cached = _cache.get(cache_key)
    now = time.time()
    if cached and now - cached["time"] < CACHE_TTL:
        return cached["data"], None

    try:
        response = requests.get(f"{BASE_URL}{path}", params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        _cache[cache_key] = {"time": now, "data": data}
        return data, None
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        return None, f"{path} returned HTTP {status}"
    except requests.RequestException as exc:
        return None, f"{path} request failed: {exc}"
    except ValueError:
        return None, f"{path} returned invalid JSON"


def _is_radiant(player_slot: Any) -> bool:
    return _safe_int(player_slot) < 128


def _did_win(match: Dict[str, Any]) -> bool:
    radiant_win = bool(match.get("radiant_win"))
    return radiant_win == _is_radiant(match.get("player_slot"))


def _hero_name(hero_id: int) -> str:
    return HEROES_CN.get(hero_id) or HEROES_EN.get(hero_id) or f"英雄 {hero_id}"


def _duration_text(seconds: int) -> str:
    minutes = max(seconds, 0) // 60
    remainder = max(seconds, 0) % 60
    return f"{minutes}:{remainder:02d}"


def _played_at(start_time: Any) -> str:
    ts = _safe_int(start_time)
    if not ts:
        return ""
    return datetime.fromtimestamp(ts, tz=CN_TZ).strftime("%Y-%m-%d %H:%M")


def _kda(kills: int, deaths: int, assists: int) -> float:
    return _round((kills + assists) / max(deaths, 1), 2)


def _form_score(match: Dict[str, Any]) -> int:
    kills = _safe_int(match.get("kills"))
    deaths = _safe_int(match.get("deaths"))
    assists = _safe_int(match.get("assists"))
    score = kills * 3 + assists * 1.4 - deaths * 2
    if _did_win(match):
        score += 12
    return max(0, min(100, int(score + 35)))


def _role_payload(lane_role: int) -> Dict[str, Any]:
    lane_name = LANE_ROLE_NAMES.get(lane_role, "分路未知")

    return {
        "lane_role_name": lane_name,
        "role_name": lane_name,
        "role_source": "parsed" if lane_role > 0 else "unknown",
    }


def _item_payload(item_id: Any) -> Dict[str, Any]:
    item_id_int = _safe_int(item_id)
    return {"item_id": item_id_int, "icon": get_item_icon_url(item_id_int)}


def _player_match_detail(account_id: int, match_id: str) -> Tuple[str, Optional[Dict[str, Any]], Optional[str]]:
    data, warning = _cached_get(f"/matches/{match_id}", timeout=12)
    if warning:
        return match_id, None, warning
    if not isinstance(data, dict):
        return match_id, None, f"/matches/{match_id} returned unexpected data"

    players = data.get("players", [])
    if not isinstance(players, list):
        return match_id, None, f"/matches/{match_id} missing players"

    player = next((entry for entry in players if _safe_int(entry.get("account_id"), -1) == account_id), None)
    if not player:
        return match_id, None, f"/matches/{match_id} missing player {account_id}"

    item_ids = [_safe_int(player.get(f"item_{index}")) for index in range(6)]
    items = [_item_payload(item_id) for item_id in item_ids]
    neutral_item = _item_payload(player.get("item_neutral"))
    lane_role = _safe_int(player.get("lane_role"))
    kills = _safe_int(player.get("kills"))
    deaths = _safe_int(player.get("deaths"))
    assists = _safe_int(player.get("assists"))
    benchmarks = player.get("benchmarks") if isinstance(player.get("benchmarks"), dict) else {}
    replay_parsed = bool(data.get("version")) and any(
        isinstance(player.get(field), list) and len(player.get(field) or []) > 0
        for field in ("gold_t", "xp_t", "lh_t", "purchase_log", "obs_log", "sen_log")
    )

    return match_id, {
        "detail_available": True,
        "benchmark_available": bool(benchmarks),
        "benchmarks": benchmarks,
        "replay_parsed": replay_parsed,
        "evidence_level": "parsed" if replay_parsed else "verified",
        "kills": kills,
        "deaths": deaths,
        "assists": assists,
        "kda": _kda(kills, deaths, assists),
        "lane_role": lane_role,
        **_role_payload(lane_role),
        "level": _safe_int(player.get("level")),
        "gold_per_min": _safe_int(player.get("gold_per_min")),
        "xp_per_min": _safe_int(player.get("xp_per_min")),
        "last_hits": _safe_int(player.get("last_hits")),
        "denies": _safe_int(player.get("denies")),
        "net_worth": _safe_int(player.get("net_worth")),
        "hero_damage": _safe_int(player.get("hero_damage")),
        "tower_damage": _safe_int(player.get("tower_damage")),
        "hero_healing": _safe_int(player.get("hero_healing")),
        "items": items,
        "item_icons": [item["icon"] for item in items],
        "neutral_item": neutral_item,
        "item_neutral_icon": neutral_item["icon"],
        "opendota_url": f"https://www.opendota.com/matches/{match_id}",
    }, None


def _enrich_match_details(account_id: int, matches: List[Dict[str, Any]]) -> List[str]:
    detail_targets = [match for match in matches[:MATCH_DETAIL_LIMIT] if match.get("match_id")]
    if not detail_targets:
        return []

    warnings = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_map = {
            executor.submit(_player_match_detail, account_id, match["match_id"]): match
            for match in detail_targets
        }
        for future in as_completed(future_map):
            match = future_map[future]
            try:
                _, detail, warning = future.result()
            except Exception as exc:
                warnings.append(f"/matches/{match['match_id']} detail failed: {exc}")
                continue
            if warning:
                warnings.append(warning)
            if detail:
                match.update(detail)

    return warnings[:6]


def _summarize_streak(matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not matches:
        return {"count": 0, "label": ""}

    first = matches[0]["win"]
    count = 0
    for match in matches:
        if match["win"] != first:
            break
        count += 1
    return {"count": count, "label": "连胜" if first else "连败"}


def _aggregate_recent(raw_matches: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    sorted_matches = sorted(raw_matches, key=lambda m: _safe_int(m.get("start_time")), reverse=True)
    enriched = []
    for match in sorted_matches[:limit]:
        hero_id = _safe_int(match.get("hero_id"))
        kills = _safe_int(match.get("kills"))
        deaths = _safe_int(match.get("deaths"))
        assists = _safe_int(match.get("assists"))
        duration = _safe_int(match.get("duration"))
        win = _did_win(match)
        lane_role = _safe_int(match.get("lane_role"))
        role = _role_payload(lane_role)
        enriched.append({
            "match_id": str(match.get("match_id", "")),
            "hero_id": hero_id,
            "hero_name": _hero_name(hero_id),
            "hero_icon": get_hero_icon_url(hero_id),
            "win": win,
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "kda": _kda(kills, deaths, assists),
            "duration": duration,
            "duration_text": _duration_text(duration),
            "start_time": _safe_int(match.get("start_time")),
            "played_at": _played_at(match.get("start_time")),
            "game_mode": GAME_MODES.get(_safe_int(match.get("game_mode")), str(match.get("game_mode") or "Unknown")),
            "lobby_type": LOBBY_TYPES.get(_safe_int(match.get("lobby_type")), str(match.get("lobby_type") or "Unknown")),
            "party_size": _safe_int(match.get("party_size")),
            "lane_role": lane_role,
            **role,
            "form_score": _form_score(match),
            "detail_available": False,
            "benchmark_available": False,
            "benchmarks": {},
            "replay_parsed": False,
            "evidence_level": "limited",
            "level": 0,
            "gold_per_min": 0,
            "xp_per_min": 0,
            "last_hits": 0,
            "denies": 0,
            "net_worth": 0,
            "hero_damage": 0,
            "tower_damage": 0,
            "hero_healing": 0,
            "items": [],
            "item_icons": [],
            "neutral_item": {"item_id": 0, "icon": ""},
            "item_neutral_icon": "",
            "opendota_url": f"https://www.opendota.com/matches/{match.get('match_id', '')}",
        })
    return enriched


def _summary(matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    games = len(matches)
    wins = sum(1 for match in matches if match["win"])
    losses = games - wins
    kills = sum(match["kills"] for match in matches)
    deaths = sum(match["deaths"] for match in matches)
    assists = sum(match["assists"] for match in matches)
    duration = sum(match["duration"] for match in matches)
    recent = matches[:10]
    previous = matches[10:20]

    def bucket_stats(bucket: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not bucket:
            return {"games": 0, "win_rate": 0, "kda": 0, "form_score": 0}
        bucket_wins = sum(1 for match in bucket if match["win"])
        return {
            "games": len(bucket),
            "win_rate": _round(bucket_wins / len(bucket) * 100),
            "kda": _round(sum(match["kda"] for match in bucket) / len(bucket), 2),
            "form_score": _round(sum(match["form_score"] for match in bucket) / len(bucket)),
        }

    recent_stats = bucket_stats(recent)
    previous_stats = bucket_stats(previous)

    return {
        "games": games,
        "wins": wins,
        "losses": losses,
        "win_rate": _round(wins / games * 100) if games else 0,
        "avg_kills": _round(kills / games) if games else 0,
        "avg_deaths": _round(deaths / games) if games else 0,
        "avg_assists": _round(assists / games) if games else 0,
        "avg_kda": _round(sum(match["kda"] for match in matches) / games, 2) if games else 0,
        "avg_duration_min": _round(duration / games / 60) if games else 0,
        "avg_form_score": _round(sum(match["form_score"] for match in matches) / games) if games else 0,
        "streak": _summarize_streak(matches),
        "last_played": matches[0]["played_at"] if matches else "",
        "trend": {
            "recent": recent_stats,
            "previous": previous_stats,
            "win_rate_diff": _round(recent_stats["win_rate"] - previous_stats["win_rate"]),
            "kda_diff": _round(recent_stats["kda"] - previous_stats["kda"], 2),
            "form_diff": _round(recent_stats["form_score"] - previous_stats["form_score"]),
        },
    }


def _hero_pool(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[int, Dict[str, Any]] = {}
    for match in matches:
        hero_id = match["hero_id"]
        if hero_id not in grouped:
            grouped[hero_id] = {
                "hero_id": hero_id,
                "hero_name": match["hero_name"],
                "hero_icon": match["hero_icon"],
                "games": 0,
                "wins": 0,
                "kills": 0,
                "deaths": 0,
                "assists": 0,
                "last_played": match["played_at"],
            }
        entry = grouped[hero_id]
        entry["games"] += 1
        entry["wins"] += 1 if match["win"] else 0
        entry["kills"] += match["kills"]
        entry["deaths"] += match["deaths"]
        entry["assists"] += match["assists"]

    result = []
    for entry in grouped.values():
        games = entry["games"]
        result.append({
            **entry,
            "win_rate": _round(entry["wins"] / games * 100) if games else 0,
            "avg_kda": _round((entry["kills"] + entry["assists"]) / max(entry["deaths"], 1), 2),
        })
    return sorted(result, key=lambda h: (-h["games"], -h["win_rate"], h["hero_name"]))[:12]


def _lifetime_heroes(raw_heroes: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_heroes, list):
        return []

    heroes = []
    for hero in raw_heroes:
        games = _safe_int(hero.get("games"))
        if games <= 0:
            continue
        wins = _safe_int(hero.get("win"))
        hero_id = _safe_int(hero.get("hero_id"))
        heroes.append({
            "hero_id": hero_id,
            "hero_name": _hero_name(hero_id),
            "hero_icon": get_hero_icon_url(hero_id),
            "games": games,
            "wins": wins,
            "win_rate": _round(wins / games * 100) if games else 0,
        })
    return sorted(heroes, key=lambda h: (-h["games"], -h["win_rate"], h["hero_name"]))[:12]


def _rank_history(raw_ratings: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_ratings, list):
        return []
    history = []
    for rating in raw_ratings[-30:]:
        tier = _safe_int(rating.get("rank_tier"))
        history.append({
            "date": str(rating.get("time", ""))[:10],
            "tier": tier,
            "label": get_rank_name_simple(tier),
        })
    return history


def _rolling_winrate(matches: List[Dict[str, Any]], window: int = 10) -> List[Dict[str, Any]]:
    chronological = list(reversed(matches))
    if len(chronological) < window:
        return []
    result = []
    for index in range(window, len(chronological) + 1):
        chunk = chronological[index - window:index]
        wins = sum(1 for match in chunk if match["win"])
        result.append({"index": index, "winrate": _round(wins / window * 100)})
    return result


def _time_analysis(matches: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    slot_keys = ["凌晨", "上午", "下午", "晚上"]
    slots = {key: {"games": 0, "wins": 0} for key in slot_keys}
    day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    days = {key: {"games": 0, "wins": 0} for key in day_names}

    for match in matches:
        ts = match["start_time"]
        if not ts:
            continue
        played = datetime.fromtimestamp(ts, tz=CN_TZ)
        hour = played.hour
        if hour < 6:
            slot = slot_keys[0]
        elif hour < 12:
            slot = slot_keys[1]
        elif hour < 18:
            slot = slot_keys[2]
        else:
            slot = slot_keys[3]
        slots[slot]["games"] += 1
        days[day_names[played.weekday()]]["games"] += 1
        if match["win"]:
            slots[slot]["wins"] += 1
            days[day_names[played.weekday()]]["wins"] += 1

    def convert(source: Dict[str, Dict[str, int]], order: List[str]) -> List[Dict[str, Any]]:
        result = []
        for label in order:
            games = source[label]["games"]
            wins = source[label]["wins"]
            result.append({
                "label": label,
                "games": games,
                "wins": wins,
                "winrate": _round(wins / games * 100) if games else 0,
            })
        return result

    return convert(slots, slot_keys), convert(days, day_names)


def _counts_summary(raw_counts: Any) -> Dict[str, List[Dict[str, Any]]]:
    if not isinstance(raw_counts, dict):
        return {}

    def format_counts(raw: Dict[str, Any], labels: Dict[int, str]) -> List[Dict[str, Any]]:
        result = []
        for key, value in raw.items():
            games = _safe_int(value.get("games"))
            wins = _safe_int(value.get("win"))
            if games <= 0:
                continue
            numeric_key = _safe_int(key, -1)
            result.append({
                "label": labels.get(numeric_key, str(key)),
                "games": games,
                "wins": wins,
                "winrate": _round(wins / games * 100) if games else 0,
            })
        return sorted(result, key=lambda item: -item["games"])[:8]

    return {
        "game_mode": format_counts(raw_counts.get("game_mode", {}), GAME_MODES),
        "lobby_type": format_counts(raw_counts.get("lobby_type", {}), LOBBY_TYPES),
        "lane_role": format_counts(raw_counts.get("lane_role", {}), LANE_ROLE_NAMES),
    }


def _hero_stat_id(raw: Dict[str, Any]) -> int:
    return _safe_int(raw.get("hero_id") or raw.get("id"))


def _hero_stat_index(raw_hero_stats: Any) -> Dict[int, Dict[str, Any]]:
    if not isinstance(raw_hero_stats, list):
        return {}
    indexed = {}
    for hero in raw_hero_stats:
        if not isinstance(hero, dict):
            continue
        hero_id = _hero_stat_id(hero)
        if hero_id:
            indexed[hero_id] = hero
    return indexed


def _role_sample(hero: Dict[str, Any], role_key: str) -> Tuple[int, int]:
    if role_key != "overall":
        return 0, 0
    return _safe_int(hero.get("pub_pick")), _safe_int(hero.get("pub_win"))


def _meta_score(win_rate: float, matches: int) -> int:
    sample_bonus = min(600, math.log10(max(matches, 1)) * 120)
    lift_bonus = max(0, win_rate - 50) * 45
    return int(win_rate * 50 + sample_bonus + lift_bonus)


def _meta_entry(hero: Dict[str, Any], role_key: str, max_matches: int = 1) -> Optional[Dict[str, Any]]:
    hero_id = _hero_stat_id(hero)
    matches, wins = _role_sample(hero, role_key)
    if not hero_id or matches <= 0:
        return None

    role_label = next((scope["label"] for scope in META_SCOPES if scope["key"] == role_key), "All Public")
    win_rate = _round(wins / matches * 100)
    contest_rate = _round(matches / max(max_matches, 1) * 100)
    return {
        "hero_id": hero_id,
        "hero_name": _hero_name(hero_id),
        "hero_icon": get_hero_icon_url(hero_id),
        "role_key": role_key,
        "role_label": role_label,
        "matches": matches,
        "wins": wins,
        "win_rate": win_rate,
        "meta_score": _meta_score(win_rate, matches),
        "contest_rate": min(contest_rate, 100),
        "pro_pick": _safe_int(hero.get("pro_pick")),
        "pro_win": _safe_int(hero.get("pro_win")),
    }


def _hero_meta(raw_hero_stats: Any) -> Dict[str, Any]:
    hero_stats = _hero_stat_index(raw_hero_stats)
    if not hero_stats:
        return {"source": "OpenDota /heroStats pub_pick/pub_win", "roles": META_SCOPES, "top": [], "by_scope": {}}

    overall_samples = [_role_sample(hero, "overall")[0] for hero in hero_stats.values()]
    max_overall = max(overall_samples) if overall_samples else 1

    entries = [
        entry for hero in hero_stats.values()
        if (entry := _meta_entry(hero, "overall", max_overall))
    ]
    overall = sorted(
        entries,
        key=lambda item: (-item["meta_score"], -item["win_rate"], -item["matches"], item["hero_name"]),
    )

    return {
        "source": "OpenDota /heroStats pub_pick/pub_win",
        "roles": META_SCOPES,
        "top": overall[:12],
        "by_scope": {"overall": overall},
    }


def _global_meta_overview(raw_hero_stats: Any) -> Dict[str, Any]:
    hero_meta = _hero_meta(raw_hero_stats)
    overall = hero_meta.get("by_scope", {}).get("overall", [])
    total_matches = sum(hero.get("matches", 0) for hero in overall)
    total_pro_picks = sum(hero.get("pro_pick", 0) for hero in overall)
    volume_leaders = sorted(overall, key=lambda item: (-item["matches"], -item["win_rate"]))[:12]
    pro_signal = sorted(
        [hero for hero in overall if hero.get("pro_pick", 0) > 0],
        key=lambda item: (-item["pro_pick"], -item["pro_win"], -item["meta_score"]),
    )[:12]
    high_confidence = sorted(
        [hero for hero in overall if hero.get("matches", 0) >= 1000],
        key=lambda item: (-item["win_rate"], -item["matches"], -item["meta_score"]),
    )[:12]
    highest_contest = max(overall, key=lambda item: item.get("contest_rate", 0), default=None)

    return {
        "source": "OpenDota /heroStats",
        "scope": "All public hero totals from pub_pick/pub_win; OpenDota does not provide position-split hero meta here",
        "hero_meta": hero_meta,
        "snapshot": {
            "heroes": len(overall),
            "total_matches": total_matches,
            "total_pro_picks": total_pro_picks,
            "top_contested_hero": highest_contest["hero_name"] if highest_contest else "",
            "top_contested_rate": highest_contest["contest_rate"] if highest_contest else 0,
        },
        "role_leaders": {},
        "volume_leaders": volume_leaders,
        "pro_signal": pro_signal,
        "high_confidence": high_confidence,
    }


def _meta_fit(
    hero_pool: List[Dict[str, Any]],
    lifetime_heroes: List[Dict[str, Any]],
    matches: List[Dict[str, Any]],
    raw_hero_stats: Any,
) -> List[Dict[str, Any]]:
    hero_stats = _hero_stat_index(raw_hero_stats)
    candidates = hero_pool[:8] or lifetime_heroes[:8]
    result = []

    for hero in candidates:
        hero_id = _safe_int(hero.get("hero_id"))
        raw_meta = hero_stats.get(hero_id)
        if not raw_meta:
            continue
        entry = _meta_entry(raw_meta, "overall")
        if not entry:
            continue
        personal_win_rate = float(hero.get("win_rate", 0))
        gap = _round(personal_win_rate - entry["win_rate"])
        if hero.get("games", 0) >= 3 and gap >= 8:
            verdict = "个人优势"
        elif entry["win_rate"] >= 52 and gap >= -3:
            verdict = "顺版本"
        elif gap <= -8:
            verdict = "需要复盘"
        else:
            verdict = "样本观察"
        result.append({
            "hero_id": hero_id,
            "hero_name": hero.get("hero_name") or _hero_name(hero_id),
            "hero_icon": hero.get("hero_icon") or get_hero_icon_url(hero_id),
            "personal_games": _safe_int(hero.get("games")),
            "personal_win_rate": personal_win_rate,
            "meta_role": entry["role_label"],
            "meta_matches": entry["matches"],
            "meta_win_rate": entry["win_rate"],
            "meta_score": entry["meta_score"],
            "gap": gap,
            "verdict": verdict,
        })

    return sorted(result, key=lambda item: (-item["personal_games"], -item["gap"], -item["meta_score"]))[:8]


def _build_signatures(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[int, int], Dict[str, Any]] = {}
    for match in matches:
        hero_id = _safe_int(match.get("hero_id"))
        if not hero_id or not match.get("detail_available"):
            continue
        item_icons = [icon for icon in match.get("item_icons", []) if icon]
        if not item_icons and not match.get("item_neutral_icon"):
            continue
        lane_role = _safe_int(match.get("lane_role"))
        key = (hero_id, lane_role)
        if key not in grouped:
            grouped[key] = {
                "hero_id": hero_id,
                "hero_name": match.get("hero_name") or _hero_name(hero_id),
                "hero_icon": match.get("hero_icon") or get_hero_icon_url(hero_id),
                "lane_role": lane_role,
                "lane_role_name": match.get("lane_role_name") or LANE_ROLE_NAMES.get(lane_role, "分路未知"),
                "role_name": match.get("role_name", "分路未解析"),
                "games": 0,
                "wins": 0,
                "kills": 0,
                "deaths": 0,
                "assists": 0,
                "items": Counter(),
                "item_icons": {},
            }
        entry = grouped[key]
        entry["games"] += 1
        entry["wins"] += 1 if match.get("win") else 0
        entry["kills"] += _safe_int(match.get("kills"))
        entry["deaths"] += _safe_int(match.get("deaths"))
        entry["assists"] += _safe_int(match.get("assists"))
        for item in match.get("items", []):
            item_id = _safe_int(item.get("item_id") if isinstance(item, dict) else 0)
            icon = item.get("icon") if isinstance(item, dict) else ""
            if item_id and icon:
                entry["items"][item_id] += 1
                entry["item_icons"][item_id] = icon
        neutral = match.get("neutral_item", {})
        neutral_id = _safe_int(neutral.get("item_id") if isinstance(neutral, dict) else 0)
        neutral_icon = neutral.get("icon") if isinstance(neutral, dict) else ""
        if neutral_id and neutral_icon:
            entry["items"][neutral_id] += 1
            entry["item_icons"][neutral_id] = neutral_icon

    result = []
    for entry in grouped.values():
        games = entry["games"]
        top_items = [
            {"item_id": item_id, "icon": entry["item_icons"].get(item_id, ""), "count": count}
            for item_id, count in entry["items"].most_common(7)
        ]
        result.append({
            "hero_id": entry["hero_id"],
            "hero_name": entry["hero_name"],
            "hero_icon": entry["hero_icon"],
            "lane_role": entry["lane_role"],
            "lane_role_name": entry["lane_role_name"],
            "role_name": entry["role_name"],
            "games": games,
            "wins": entry["wins"],
            "win_rate": _round(entry["wins"] / games * 100) if games else 0,
            "avg_kda": _round((entry["kills"] + entry["assists"]) / max(entry["deaths"], 1), 2),
            "items": top_items,
        })

    return sorted(result, key=lambda item: (-item["games"], -item["win_rate"], -item["avg_kda"]))[:8]


def _role_matrix(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[int, Dict[str, Any]] = {}
    for match in matches:
        lane_role = _safe_int(match.get("lane_role"))
        if not lane_role:
            continue
        if lane_role not in grouped:
            grouped[lane_role] = {
                "lane_role": lane_role,
                "lane_role_name": LANE_ROLE_NAMES.get(lane_role, "分路未知"),
                "role_name": LANE_ROLE_NAMES.get(lane_role, "分路未知"),
                "games": 0,
                "wins": 0,
                "kills": 0,
                "deaths": 0,
                "assists": 0,
                "gpm": 0,
                "xpm": 0,
                "last_hits": 0,
                "damage": 0,
                "heroes": Counter(),
            }
        entry = grouped[lane_role]
        entry["games"] += 1
        entry["wins"] += 1 if match.get("win") else 0
        entry["kills"] += _safe_int(match.get("kills"))
        entry["deaths"] += _safe_int(match.get("deaths"))
        entry["assists"] += _safe_int(match.get("assists"))
        entry["gpm"] += _safe_int(match.get("gold_per_min"))
        entry["xpm"] += _safe_int(match.get("xp_per_min"))
        entry["last_hits"] += _safe_int(match.get("last_hits"))
        entry["damage"] += _safe_int(match.get("hero_damage"))
        if match.get("hero_name"):
            entry["heroes"][match["hero_name"]] += 1

    result = []
    for entry in grouped.values():
        games = entry["games"]
        result.append({
            "lane_role": entry["lane_role"],
            "lane_role_name": entry["lane_role_name"],
            "role_name": entry["role_name"],
            "games": games,
            "win_rate": _round(entry["wins"] / games * 100) if games else 0,
            "avg_kda": _round((entry["kills"] + entry["assists"]) / max(entry["deaths"], 1), 2),
            "avg_gpm": _round(entry["gpm"] / games) if games else 0,
            "avg_xpm": _round(entry["xpm"] / games) if games else 0,
            "avg_last_hits": _round(entry["last_hits"] / games) if games else 0,
            "avg_damage": _round(entry["damage"] / games) if games else 0,
            "top_hero": entry["heroes"].most_common(1)[0][0] if entry["heroes"] else "",
        })

    return sorted(result, key=lambda item: item["lane_role"])


def _best_bucket(buckets: List[Dict[str, Any]]) -> Dict[str, Any]:
    candidates = [bucket for bucket in buckets if bucket.get("games", 0) > 0]
    if not candidates:
        return {}
    return sorted(candidates, key=lambda item: (-item["winrate"], -item["games"], item["label"]))[0]


def _weak_bucket(buckets: List[Dict[str, Any]]) -> Dict[str, Any]:
    candidates = [bucket for bucket in buckets if bucket.get("games", 0) > 0]
    if not candidates:
        return {}
    return sorted(candidates, key=lambda item: (item["winrate"], -item["games"], item["label"]))[0]


def _readiness(summary: Dict[str, Any], time_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    win_rate = float(summary.get("win_rate", 0))
    form_score = float(summary.get("avg_form_score", 0))
    streak = summary.get("streak", {})
    night = next((bucket for bucket in time_data if bucket["label"] == "凌晨"), {})

    if streak.get("label") == "连败" and streak.get("count", 0) >= 3:
        return {
            "label": "降温复盘",
            "score": max(35, int(form_score - 15)),
            "tone": "red",
            "reason": "连续失利后继续排位风险较高，优先复盘死亡和节奏断点。",
        }
    if win_rate >= 60 and form_score >= 75:
        return {
            "label": "冲分窗口",
            "score": min(96, int((win_rate + form_score) / 2)),
            "tone": "green",
            "reason": "近期胜率和状态评分都在线，可以围绕高胜率英雄继续排。",
        }
    if night and night.get("games", 0) >= 5 and night.get("winrate", 0) < 50:
        return {
            "label": "疲劳预警",
            "score": max(45, int(form_score - 8)),
            "tone": "red",
            "reason": "凌晨样本偏多且胜率偏低，建议把高强度排位移到更稳定时段。",
        }
    return {
        "label": "稳定训练",
        "score": max(50, min(88, int((win_rate + form_score) / 2))),
        "tone": "gold",
        "reason": "近期表现没有明显崩盘信号，适合按计划压缩英雄池和复盘细节。",
    }


def _coach_pack(
    summary: Dict[str, Any],
    matches: List[Dict[str, Any]],
    hero_pool: List[Dict[str, Any]],
    lifetime_heroes: List[Dict[str, Any]],
    time_data: List[Dict[str, Any]],
    weekday_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    readiness = _readiness(summary, time_data)
    best_recent_hero = next((hero for hero in hero_pool if hero.get("games", 0) >= 2), hero_pool[0] if hero_pool else {})
    signature_hero = next((hero for hero in lifetime_heroes if hero.get("games", 0) >= 20 and hero.get("win_rate", 0) >= 52), lifetime_heroes[0] if lifetime_heroes else {})
    weak_time = _weak_bucket(time_data)
    best_day = _best_bucket(weekday_data)
    losses = [match for match in matches if not match["win"]]
    high_death_losses = [match for match in losses if match["deaths"] >= 8]
    recent_ten = matches[:10]
    recent_deaths = _round(sum(match["deaths"] for match in recent_ten) / len(recent_ten)) if recent_ten else 0

    insights = []
    if best_recent_hero:
        insights.append({
            "title": "主打英雄",
            "metric": f"{best_recent_hero['win_rate']}% / {best_recent_hero['games']}场",
            "body": f"近期最值得继续排的是 {best_recent_hero['hero_name']}，保持同一分路和前 15 分钟节奏。",
            "action": f"下一组 BO3 优先选择 {best_recent_hero['hero_name']}。",
            "tone": "green" if best_recent_hero.get("win_rate", 0) >= 50 else "gold",
        })
    if high_death_losses:
        insights.append({
            "title": "输局死亡",
            "metric": f"{len(high_death_losses)}/{len(losses) or 1} 局",
            "body": "近期输局里高死亡样本偏多；未解析 replay 时无法可靠判断具体位置和团战原因。",
            "action": "下一组三局手动标记每次死亡属于带线、接团、救人或操作失误。",
            "tone": "red",
        })
    if weak_time:
        insights.append({
            "title": "时间窗口",
            "metric": f"{weak_time['label']} {weak_time['winrate']}%",
            "body": f"{weak_time['label']} 的结果最差，不适合作为冲分主时段。",
            "action": "状态不稳时只在该时段打普通或练英雄。",
            "tone": "red" if weak_time.get("winrate", 0) < 45 else "gold",
        })
    if best_day:
        insights.append({
            "title": "高胜率日",
            "metric": f"{best_day['label']} {best_day['winrate']}%",
            "body": f"{best_day['label']} 表现最好，适合安排高质量排位或组排。",
            "action": "把最熟练的 2 个英雄留给该窗口。",
            "tone": "cyan",
        })

    while len(insights) < 4:
        insights.append({
            "title": "样本积累",
            "metric": f"{summary.get('games', 0)}场",
            "body": "继续积累公开比赛数据后，诊断会更稳定。",
            "action": "保持公开比赛数据，并至少分析最近 20 场。",
            "tone": "gold",
        })

    training_plan = [
        {
            "label": "今天",
            "focus": "压缩英雄池",
            "drill": f"只打 {best_recent_hero.get('hero_name') or signature_hero.get('hero_name') or '当前最高胜率英雄'}，连续 3 场记录死亡原因。",
            "success_metric": "死亡数低于近期均值",
        },
        {
            "label": "明天",
            "focus": "节奏复盘",
            "drill": "复盘最近 2 场失败局，标记第一个经济断点和第一波无收益死亡。",
            "success_metric": "前 20 分钟少 1 次无收益死亡",
        },
        {
            "label": "本周",
            "focus": "稳定上分",
            "drill": f"避开 {weak_time.get('label', '低胜率时段')}，在胜率更高的窗口打排位。",
            "success_metric": "本周胜率高于生涯胜率",
        },
    ]

    pro_preview = [
        {"title": "职业样本对比", "detail": "把你的出装、技能和时间点与高分局同英雄样本比较。"},
        {"title": "BP 推荐", "detail": "根据你自己的英雄池、当前版本和对位风险给出推荐。"},
        {"title": "复盘导出", "detail": "把最近比赛自动整理成可分享的训练报告。"},
        {"title": "队伍空间", "detail": "追踪多个账号、队友组合和分路搭配。"},
    ]

    return {
        "readiness": readiness,
        "insights": insights[:4],
        "training_plan": training_plan,
        "signature_hero": signature_hero,
        "recent_deaths": recent_deaths,
        "pro_preview": pro_preview,
    }


def _profile(account_id: int, raw_profile: Any, wl: Any) -> Dict[str, Any]:
    profile = raw_profile.get("profile", {}) if isinstance(raw_profile, dict) else {}
    rank_tier = _safe_int(raw_profile.get("rank_tier") if isinstance(raw_profile, dict) else None)
    rank_name, rank_icon = get_rank_name(rank_tier)
    wins = _safe_int(wl.get("win") if isinstance(wl, dict) else 0)
    losses = _safe_int(wl.get("lose") if isinstance(wl, dict) else 0)
    total = wins + losses
    return {
        "account_id": account_id,
        "username": profile.get("personaname") or f"Player {account_id}",
        "avatar": profile.get("avatarfull") or profile.get("avatarmedium") or "",
        "profile_url": profile.get("profileurl") or "",
        "country": profile.get("loccountrycode") or "",
        "rank_tier": rank_tier,
        "rank_name": rank_name,
        "rank_icon": rank_icon,
        "leaderboard_rank": raw_profile.get("leaderboard_rank") if isinstance(raw_profile, dict) else None,
        "total_wins": wins,
        "total_losses": losses,
        "total_games": total,
        "lifetime_win_rate": _round(wins / total * 100) if total else 0,
    }


@router.get("/players/search")
def search_players(q: str = Query(..., min_length=2), limit: int = Query(8, ge=1, le=20)):
    data, warning = _cached_get("/search", {"q": q}, timeout=18)
    results = []
    if isinstance(data, list):
        for player in data[:limit]:
            results.append({
                "account_id": player.get("account_id"),
                "username": player.get("personaname") or f"Player {player.get('account_id')}",
                "avatar": player.get("avatarfull") or player.get("avatarmedium") or "",
                "last_match_time": player.get("last_match_time") or "",
                "similarity": player.get("similarity"),
            })
    return {"results": results, "warnings": [warning] if warning else []}


@router.get("/meta/overview")
def meta_overview():
    hero_stats_raw, warning = _cached_get("/heroStats", timeout=12)
    overview = _global_meta_overview(hero_stats_raw)
    return {
        **overview,
        "warnings": [warning] if warning else [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _fetch_player_sources(account_id: int, include_deep: bool = True, limit: int = 50) -> Tuple[Dict[str, Any], List[str]]:
    requests_to_make = {
        "profile": (f"/players/{account_id}", None, 10),
        "recent": (f"/players/{account_id}/matches", {"limit": min(limit, 100)}, 12),
    }
    if include_deep:
        requests_to_make.update({
            "wl": (f"/players/{account_id}/wl", None, 10),
            "heroes": (f"/players/{account_id}/heroes", None, 12),
            "ratings": (f"/players/{account_id}/ratings", None, 12),
            "counts": (f"/players/{account_id}/counts", None, 12),
            "hero_stats": ("/heroStats", None, 12),
        })

    values: Dict[str, Any] = {}
    warnings: List[str] = []
    with ThreadPoolExecutor(max_workers=len(requests_to_make)) as executor:
        futures = {
            executor.submit(_cached_get, path, params, timeout): key
            for key, (path, params, timeout) in requests_to_make.items()
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                value, warning = future.result()
            except Exception as exc:
                values[key] = None
                warnings.append(f"{key} request failed: {exc}")
                continue
            values[key] = value
            if warning:
                warnings.append(warning)

    return values, warnings


def _empty_hero_meta() -> Dict[str, Any]:
    return {
        "source": "OpenDota /heroStats pub_pick/pub_win",
        "roles": META_SCOPES,
        "top": [],
        "by_scope": {},
    }


def _player_quick_payload(account_id: int, limit: int) -> Dict[str, Any]:
    sources, warnings = _fetch_player_sources(account_id, include_deep=False, limit=limit)
    recent_matches = _aggregate_recent(sources.get("recent") if isinstance(sources.get("recent"), list) else [], min(limit, 20))
    summary = _summary(recent_matches)
    hero_pool = _hero_pool(recent_matches)
    lifetime_heroes = _lifetime_heroes(sources.get("heroes"))
    time_data, weekday_data = _time_analysis(recent_matches)

    return {
        "profile": _profile(account_id, sources.get("profile") or {}, sources.get("wl") or {}),
        "summary": summary,
        "recent_matches": recent_matches,
        "hero_pool": hero_pool,
        "lifetime_heroes": lifetime_heroes,
        "hero_meta": _empty_hero_meta(),
        "meta_fit": [],
        "build_signatures": [],
        "role_matrix": [],
        "rank_history": [],
        "rolling_winrate": _rolling_winrate(recent_matches),
        "time_analysis": time_data,
        "weekday_analysis": weekday_data,
        "counts": {},
        "coach": _coach_pack(summary, recent_matches, hero_pool, lifetime_heroes, time_data, weekday_data),
        "warnings": warnings,
        "data_stage": "quick",
        "updated_at": datetime.now(tz=CN_TZ).strftime("%Y-%m-%d %H:%M:%S"),
    }


def _player_dashboard_payload(account_id: int, limit: int) -> Dict[str, Any]:
    sources, warnings = _fetch_player_sources(account_id, include_deep=True, limit=limit)
    profile_raw = sources.get("profile")
    recent_raw = sources.get("recent")
    wl_raw = sources.get("wl")
    heroes_raw = sources.get("heroes")
    ratings_raw = sources.get("ratings")
    counts_raw = sources.get("counts")
    hero_stats_raw = sources.get("hero_stats")

    recent_matches = _aggregate_recent(recent_raw if isinstance(recent_raw, list) else [], limit)
    warnings.extend(_enrich_match_details(account_id, recent_matches))
    summary = _summary(recent_matches)
    hero_pool = _hero_pool(recent_matches)
    lifetime_heroes = _lifetime_heroes(heroes_raw)
    time_data, weekday_data = _time_analysis(recent_matches)

    return {
        "profile": _profile(account_id, profile_raw or {}, wl_raw or {}),
        "summary": summary,
        "recent_matches": recent_matches,
        "hero_pool": hero_pool,
        "lifetime_heroes": lifetime_heroes,
        "hero_meta": _hero_meta(hero_stats_raw),
        "meta_fit": _meta_fit(hero_pool, lifetime_heroes, recent_matches, hero_stats_raw),
        "build_signatures": _build_signatures(recent_matches),
        "role_matrix": _role_matrix(recent_matches),
        "rank_history": _rank_history(ratings_raw),
        "rolling_winrate": _rolling_winrate(recent_matches),
        "time_analysis": time_data,
        "weekday_analysis": weekday_data,
        "counts": _counts_summary(counts_raw),
        "coach": _coach_pack(summary, recent_matches, hero_pool, lifetime_heroes, time_data, weekday_data),
        "warnings": warnings,
        "data_stage": "deep",
        "updated_at": datetime.now(tz=CN_TZ).strftime("%Y-%m-%d %H:%M:%S"),
    }


def _review_match_sample(matches: List[Dict[str, Any]], limit: int = 20) -> List[Dict[str, Any]]:
    sample = []
    for match in matches[:limit]:
        sample.append({
            "match_id": match.get("match_id"),
            "hero": match.get("hero_name"),
            "result": "win" if match.get("win") else "loss",
            "kda": f"{match.get('kills', 0)}/{match.get('deaths', 0)}/{match.get('assists', 0)}",
            "kda_score": match.get("kda", 0),
            "lane": match.get("role_name"),
            "duration": match.get("duration_text"),
            "gpm": match.get("gold_per_min", 0),
            "xpm": match.get("xp_per_min", 0),
            "last_hits": match.get("last_hits", 0),
            "hero_damage": match.get("hero_damage", 0),
            "tower_damage": match.get("tower_damage", 0),
            "form_score": match.get("form_score", 0),
            "played_at": match.get("played_at"),
            "evidence_level": match.get("evidence_level", "limited"),
            "replay_parsed": bool(match.get("replay_parsed")),
            "benchmark_available": bool(match.get("benchmark_available")),
        })
    return sample


def _top_loss_matches(matches: List[Dict[str, Any]], limit: int = 3) -> List[Dict[str, Any]]:
    losses = [match for match in matches if not match.get("win")]
    ranked = sorted(losses, key=lambda match: (-_safe_int(match.get("deaths")), _safe_int(match.get("form_score"))))
    result = []
    for match in ranked[:limit]:
        result.append({
            "match_id": match.get("match_id"),
            "hero": match.get("hero_name"),
            "reason": f"{match.get('deaths', 0)} 死，{match.get('role_name', '分路未解析')}，KDA {match.get('kda', 0)}",
        })
    return result


def _fallback_review(payload: Dict[str, Any]) -> Dict[str, Any]:
    profile = payload.get("profile", {})
    summary = payload.get("summary", {})
    matches = payload.get("recent_matches", [])
    hero_pool = payload.get("hero_pool", [])
    meta_fit = payload.get("meta_fit", [])
    time_data = payload.get("time_analysis", [])
    role_matrix = payload.get("role_matrix", [])
    coach = payload.get("coach", {})

    games = _safe_int(summary.get("games"))
    win_rate = float(summary.get("win_rate", 0))
    avg_deaths = float(summary.get("avg_deaths", 0))
    trend = summary.get("trend", {})
    high_death_losses = [match for match in matches if not match.get("win") and _safe_int(match.get("deaths")) >= 8]
    best_hero = next((hero for hero in hero_pool if hero.get("games", 0) >= 2), hero_pool[0] if hero_pool else {})
    weak_hero = next((hero for hero in hero_pool if hero.get("games", 0) >= 2 and hero.get("win_rate", 0) < 50), {})
    meta_gap = next((item for item in meta_fit if item.get("verdict") == "需要复盘"), None)
    best_role = sorted(role_matrix, key=lambda item: (-item.get("win_rate", 0), -item.get("games", 0)))[0] if role_matrix else {}
    weak_time = sorted(
        [bucket for bucket in time_data if bucket.get("games", 0) > 0],
        key=lambda item: (item.get("winrate", 0), -item.get("games", 0)),
    )[0] if time_data else {}

    if win_rate >= 58:
        headline = "近期状态可继续冲分，但要把胜利条件固定下来"
    elif win_rate >= 50:
        headline = "整体可打，主要收益来自减少输局死亡"
    else:
        headline = "近期胜率偏低，先暂停盲排并复盘输局节奏"

    sections = [
        {
            "title": "最高优先级",
            "finding": f"最近 {games} 场胜率 {win_rate}%，均死 {avg_deaths}，输局里有 {len(high_death_losses)} 场死亡达到 8 次以上。",
            "evidence": f"近期 10 场相对前 10 场：胜率 {_signed(_round(float(trend.get('win_rate_diff', 0))), '%')}，KDA {_signed(_round(float(trend.get('kda_diff', 0)), 2))}。",
            "action": "下一组三局记录每次死亡的类别；没有 replay 事件时不判断具体位置或团战原因。",
        },
        {
            "title": "英雄池",
            "finding": (
                f"当前最值得保留的是 {best_hero.get('hero_name')}：{best_hero.get('games', 0)} 场，胜率 {best_hero.get('win_rate', 0)}%。"
                if best_hero else "近期英雄池样本不足，先固定 2 个主打英雄再评估。"
            ),
            "evidence": (
                f"{weak_hero.get('hero_name')} 近期胜率 {weak_hero.get('win_rate')}%，建议暂时移出上分池。"
                if weak_hero else "没有明显拖后腿英雄，继续扩大主打英雄样本。"
            ),
            "action": f"今天只围绕 {best_hero.get('hero_name') or '最高熟练度英雄'} 打 3 场，输一场就复盘前 12 分钟第一波节奏断点。",
        },
        {
            "title": "版本与个人差距",
            "finding": (
                f"{meta_gap.get('hero_name')} 个人胜率比全局低 {abs(meta_gap.get('gap', 0))} 个百分点，属于优先复盘英雄。"
                if meta_gap else "你的近期英雄暂时没有明显落后全局 Meta 的样本。"
            ),
            "evidence": "全局对照来自 OpenDota heroStats 的 pub_pick/pub_win 总体样本。",
            "action": "只把全局 Meta 当作筛选器，真正决定是否继续练的是你的同英雄最近 5 场死亡和经济节奏。",
        },
        {
            "title": "分路与经济",
            "finding": (
                f"{best_role.get('role_name')} 是当前最稳定分路：{best_role.get('games', 0)} 场，胜率 {best_role.get('win_rate', 0)}%，KDA {best_role.get('avg_kda', 0)}。"
                if best_role else "近期没有足够的 OpenDota 分路解析样本。"
            ),
            "evidence": f"平均 GPM {best_role.get('avg_gpm', 0)}，平均补刀 {best_role.get('avg_last_hits', 0)}。" if best_role else "分路字段缺失时不做位置推断。",
            "action": "每局 10 分钟记录一次：补刀、死亡、TP 是否用在有效支援上，用这三项判断是否偏离分路任务。",
        },
        {
            "title": "排位窗口",
            "finding": (
                f"{weak_time.get('label')} 样本胜率最低：{weak_time.get('winrate')}%，不适合冲分。"
                if weak_time else "时段样本还不够，暂时不按时间窗口做限制。"
            ),
            "evidence": "该结论只使用当前账号近期公开比赛的开始时间。",
            "action": f"把 {weak_time.get('label', '低质量时段')} 留给练英雄或普通匹配，高质量排位放在胜率更高的时段。",
        },
    ]

    weekly_plan = [
        {"day": "Day 1", "focus": "死亡复盘", "task": "打开最近 3 场输局，只看每次死亡前 10 秒视野、技能和队友位置。", "metric": "下一组 BO3 死亡均值下降 1 次。"},
        {"day": "Day 2", "focus": "英雄池收缩", "task": f"只打 {best_hero.get('hero_name') or '主打英雄'}，不要临场换练英雄。", "metric": "同英雄连续 3 场完成固定前 10 分钟节奏。"},
        {"day": "Day 3", "focus": "经济节奏", "task": "记录结算 GPM，并在可用时查看同英雄经济百分位。", "metric": "连续三局经济百分位不低于当前基准。"},
        {"day": "Day 4", "focus": "视野习惯", "task": "查看历史眼位热图；只有 replay 已解析时才复盘单局眼位事件。", "metric": "完成三局死亡原因手动标记。"},
        {"day": "Day 5-7", "focus": "稳定上分", "task": "只在高胜率时段打排位，输两局立即停止并复盘。", "metric": "本周胜率高于最近样本胜率。"},
    ]

    return {
        "headline": headline,
        "score": coach.get("readiness", {}).get("score", 0),
        "summary": f"{profile.get('username', '该玩家')} 最近 {games} 场：{summary.get('wins', 0)} 胜 {summary.get('losses', 0)} 负，KDA {summary.get('avg_kda', 0)}，状态评分 {summary.get('avg_form_score', 0)}。",
        "sections": sections,
        "weekly_plan": weekly_plan,
        "priority_matches": _top_loss_matches(matches),
        "model_note": "规则兜底复盘：未调用外部模型或外部模型失败时使用。",
    }


def _compact_review_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    matches = payload.get("recent_matches", [])
    return {
        "profile": payload.get("profile", {}),
        "summary": payload.get("summary", {}),
        "hero_pool": payload.get("hero_pool", [])[:8],
        "meta_fit": payload.get("meta_fit", [])[:8],
        "role_matrix": payload.get("role_matrix", []),
        "time_analysis": payload.get("time_analysis", []),
        "weekday_analysis": payload.get("weekday_analysis", []),
        "build_signatures": payload.get("build_signatures", [])[:6],
        "data_quality": {
            "recent_matches": len(matches),
            "scoreboard_matches": sum(1 for match in matches if match.get("detail_available")),
            "benchmark_matches": sum(1 for match in matches if match.get("benchmark_available")),
            "replay_parsed_matches": sum(1 for match in matches if match.get("replay_parsed")),
            "parsed_lane_matches": sum(1 for match in matches if _safe_int(match.get("lane_role")) > 0),
        },
        "recent_matches": _review_match_sample(matches, limit=24),
    }


def _normalize_review(value: Any, fallback: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return fallback

    review = {
        "headline": str(value.get("headline") or fallback["headline"])[:180],
        "score": _safe_int(value.get("score"), _safe_int(fallback.get("score"))),
        "summary": str(value.get("summary") or fallback["summary"])[:600],
        "sections": value.get("sections") if isinstance(value.get("sections"), list) else fallback["sections"],
        "weekly_plan": value.get("weekly_plan") if isinstance(value.get("weekly_plan"), list) else fallback["weekly_plan"],
        "priority_matches": value.get("priority_matches") if isinstance(value.get("priority_matches"), list) else fallback["priority_matches"],
        "model_note": str(value.get("model_note") or "DeepSeek 生成复盘，已按结构化格式返回。")[:240],
    }
    review["sections"] = [
        {
            "title": str(section.get("title", "复盘项"))[:80],
            "finding": str(section.get("finding", ""))[:500],
            "evidence": str(section.get("evidence", ""))[:500],
            "action": str(section.get("action", ""))[:500],
        }
        for section in review["sections"][:6]
        if isinstance(section, dict)
    ] or fallback["sections"]
    review["weekly_plan"] = [
        {
            "day": str(step.get("day", ""))[:40],
            "focus": str(step.get("focus", ""))[:80],
            "task": str(step.get("task", ""))[:360],
            "metric": str(step.get("metric", ""))[:180],
        }
        for step in review["weekly_plan"][:7]
        if isinstance(step, dict)
    ] or fallback["weekly_plan"]
    review["priority_matches"] = [
        {
            "match_id": str(match.get("match_id", ""))[:32],
            "hero": str(match.get("hero", ""))[:80],
            "reason": str(match.get("reason", ""))[:240],
        }
        for match in review["priority_matches"][:5]
        if isinstance(match, dict)
    ]
    return review


def _deepseek_review(payload: Dict[str, Any], fallback: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return None, "DEEPSEEK_API_KEY is not configured"

    instructions = (
        "你是一个面向付费用户的 Dota 2 复盘教练。"
        "基于输入 JSON 输出严格 JSON，不要 Markdown。"
        "必须用中文，必须给出证据和可执行动作，避免泛泛而谈。"
        "严格遵守证据边界：只有 replay_parsed=true 时才能声称具体团战、死亡位置、眼位事件、购买时间或分钟级经济断点；"
        "否则只能使用结算数据、百分位和用户可自行记录的训练动作，并明确说明数据限制。"
        "不要根据英雄或 KDA 推断分路。"
        "输出字段：headline, score, summary, sections, weekly_plan, priority_matches, model_note。"
        "sections 每项包含 title, finding, evidence, action；weekly_plan 每项包含 day, focus, task, metric。"
    )
    request_body = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": instructions},
            {
                "role": "user",
                "content": json.dumps(_compact_review_context(payload), ensure_ascii=False),
            },
        ],
        "temperature": 0.35,
        "response_format": {"type": "json_object"},
    }

    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=request_body,
            timeout=45,
        )
        if response.status_code >= 400:
            return None, f"DeepSeek returned HTTP {response.status_code}"
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed = json.loads(content)
        return _normalize_review(parsed, fallback), None
    except requests.RequestException as exc:
        return None, f"DeepSeek request failed: {exc.__class__.__name__}"
    except (ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError):
        return None, "DeepSeek returned an unreadable response"


def _preview_review(review: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **review,
        "sections": review.get("sections", [])[:2],
        "weekly_plan": review.get("weekly_plan", [])[:2],
        "priority_matches": review.get("priority_matches", [])[:2],
        "model_note": "免费预览只展示部分结论，完整 AI 复盘需要 Pro 解锁。",
    }


def _bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        return ""
    prefix = "Bearer "
    if authorization.startswith(prefix):
        return authorization[len(prefix):].strip()
    return authorization.strip()


SCORECARD_METRICS = {
    "gold_per_min": ("经济效率", "GPM"),
    "xp_per_min": ("经验效率", "XPM"),
    "kills_per_min": ("击杀参与", "KPM"),
    "last_hits_per_min": ("补刀效率", "LH/min"),
    "hero_damage_per_min": ("英雄伤害", "HD/min"),
    "hero_healing_per_min": ("治疗贡献", "Heal/min"),
    "tower_damage": ("推进转化", "Tower"),
}

SCORECARD_ACTIONS = {
    "gold_per_min": "下一组三局只记录 10/20 分钟净值，目标是减少无收益移动和死亡后的经济断档。",
    "xp_per_min": "下一组三局记录 10 分钟等级，并检查每次离线支援是否换到击杀、塔或符。",
    "kills_per_min": "下一组三局记录前 20 分钟有效参战次数，只统计获得击杀、塔或 Roshan 的行动。",
    "last_hits_per_min": "下一组三局记录 10 分钟补刀，并把每局目标设为比当前基准多 5 个。",
    "hero_damage_per_min": "下一组三局在结算页记录英雄伤害，并检查关键技能是否用于有效目标。",
    "hero_healing_per_min": "下一组三局记录治疗量和有效团战次数，避免把治疗能力浪费在无收益交换。",
    "tower_damage": "下一组三局每次赢团后先确认能否换塔或 Roshan，把优势转成地图目标。",
}


def _match_scorecard_payload(account_id: int, match_id: str) -> Dict[str, Any]:
    data, warning = _cached_get(f"/matches/{match_id}", timeout=18)
    if warning:
        raise HTTPException(status_code=502, detail=warning)
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="OpenDota returned an invalid match")

    players = data.get("players") if isinstance(data.get("players"), list) else []
    player = next((entry for entry in players if _safe_int(entry.get("account_id"), -1) == account_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player was not found in this match")

    benchmark_raw = player.get("benchmarks") if isinstance(player.get("benchmarks"), dict) else {}
    metrics = []
    for key, (label, unit) in SCORECARD_METRICS.items():
        value = benchmark_raw.get(key)
        if not isinstance(value, dict):
            continue
        raw = float(value.get("raw") or 0)
        percentile = max(0, min(100, int(round(float(value.get("pct") or 0) * 100))))
        if key == "hero_healing_per_min" and raw <= 0:
            continue
        metrics.append({
            "key": key,
            "label": label,
            "unit": unit,
            "value": _round(raw, 1),
            "percentile": percentile,
        })

    metrics.sort(key=lambda metric: metric["percentile"], reverse=True)
    strongest = metrics[0] if metrics else None
    weakest = metrics[-1] if metrics else None
    replay_parsed = bool(data.get("version")) and any(
        isinstance(player.get(field), list) and len(player.get(field) or []) > 0
        for field in ("gold_t", "xp_t", "lh_t", "purchase_log", "obs_log", "sen_log")
    )

    if strongest and weakest:
        headline = f"{strongest['label']}是这局最强项，下一步补齐{weakest['label']}"
        finding = f"{strongest['label']}位于同英雄第 {strongest['percentile']} 百分位；{weakest['label']}位于第 {weakest['percentile']} 百分位。"
        action = SCORECARD_ACTIONS.get(weakest["key"], "下一组三局只追踪这一项，并与当前百分位比较。")
    else:
        headline = "这局只有结算数据，暂时无法生成英雄百分位对照"
        finding = "OpenDota 尚未返回该英雄的 benchmark 数据。"
        action = "保留这局作为历史记录，下一场优先查看带 benchmark 的比赛。"

    item_ids = [_safe_int(player.get(f"item_{index}")) for index in range(6)]
    kills = _safe_int(player.get("kills"))
    deaths = _safe_int(player.get("deaths"))
    assists = _safe_int(player.get("assists"))
    player_slot = _safe_int(player.get("player_slot"))
    won = bool(data.get("radiant_win")) == _is_radiant(player_slot)
    return {
        "match": {
            "match_id": str(match_id),
            "hero_id": _safe_int(player.get("hero_id")),
            "hero_name": _hero_name(_safe_int(player.get("hero_id"))),
            "hero_icon": get_hero_icon_url(_safe_int(player.get("hero_id"))),
            "win": won,
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "kda": _kda(kills, deaths, assists),
            "duration_text": _duration_text(_safe_int(data.get("duration"))),
            "played_at": _played_at(data.get("start_time")),
            "items": [_item_payload(item_id) for item_id in item_ids if item_id],
        },
        "metrics": metrics,
        "headline": headline,
        "finding": finding,
        "action": action,
        "evidence": [
            {
                "key": "scoreboard",
                "label": "结算数据",
                "status": "verified",
                "detail": "胜负、KDA、最终出装和比赛时长来自 OpenDota 比赛结算数据。",
            },
            {
                "key": "benchmarks",
                "label": "同英雄百分位",
                "status": "verified" if metrics else "unavailable",
                "detail": f"已获得 {len(metrics)} 项同英雄 benchmark。" if metrics else "OpenDota 未返回 benchmark。",
            },
            {
                "key": "replay",
                "label": "Replay 事件",
                "status": "parsed" if replay_parsed else "unavailable",
                "detail": "可分析逐分钟经济、购买和眼位事件。" if replay_parsed else "该局未解析，不判断具体团战、死亡位置或装备时间。",
            },
        ],
        "replay_parsed": replay_parsed,
        "source": "OpenDota match scoreboard + hero benchmarks",
        "updated_at": datetime.now(tz=CN_TZ).strftime("%Y-%m-%d %H:%M:%S"),
    }


@router.get("/players/{account_id}/dashboard/quick")
def player_dashboard_quick(account_id: int, limit: int = Query(20, ge=10, le=20)):
    return _player_quick_payload(account_id, limit)


@router.get("/players/{account_id}/dashboard")
def player_dashboard(account_id: int, limit: int = Query(50, ge=10, le=100)):
    return _player_dashboard_payload(account_id, limit)


@router.get("/players/{account_id}/matches/{match_id}/scorecard")
def player_match_scorecard(account_id: int, match_id: str):
    return _match_scorecard_payload(account_id, match_id)


@router.get("/players/{account_id}/review/preview")
def player_review_preview(account_id: int, limit: int = Query(30, ge=10, le=80)):
    payload = _player_quick_payload(account_id, min(limit, 20))
    review = _fallback_review(payload)
    return {
        "locked": True,
        "source": "deterministic_preview",
        "review": _preview_review(review),
        "paywall": {
            "title": "解锁完整 AI 复盘",
            "detail": "Pro 会基于最近比赛、英雄池、全局 Meta、分路和出装样本生成完整训练报告。",
        },
        "warnings": payload.get("warnings", []),
        "updated_at": datetime.now(tz=CN_TZ).strftime("%Y-%m-%d %H:%M:%S"),
    }


@router.post("/players/{account_id}/review")
def player_review(
    account_id: int,
    limit: int = Query(50, ge=10, le=100),
    request_payload: Optional[Dict[str, Any]] = Body(default=None),
    authorization: Optional[str] = Header(default=None),
):
    token = ""
    if isinstance(request_payload, dict):
        token = str(request_payload.get("access_token") or "")
    token = token or _bearer_token(authorization)

    if not verify_access_token(token, account_id):
        raise HTTPException(status_code=402, detail="Pro access is required for full AI review")

    payload = _player_dashboard_payload(account_id, limit)
    fallback = _fallback_review(payload)
    generated, warning = _deepseek_review(payload, fallback)
    source = "deepseek" if generated else "deterministic_fallback"

    warnings = list(payload.get("warnings", []))
    if warning:
        warnings.append(warning)

    return {
        "locked": False,
        "source": source,
        "review": generated or fallback,
        "warnings": warnings[:8],
        "updated_at": datetime.now(tz=CN_TZ).strftime("%Y-%m-%d %H:%M:%S"),
    }
