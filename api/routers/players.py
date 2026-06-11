"""Player dashboard API backed by public OpenDota endpoints."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from fastapi import APIRouter, Query

from fetch_dota_stats import HEROES_CN, HEROES_EN, get_hero_icon_url
from services.stats import get_item_icon_url, get_rank_name, get_rank_name_simple

router = APIRouter()

BASE_URL = "https://api.opendota.com/api"
CACHE_TTL = 180
CN_TZ = timezone(timedelta(hours=8))
MATCH_DETAIL_LIMIT = 20

LANE_ROLE_NAMES = {
    0: "分路未解析",
    1: "优势路",
    2: "中路",
    3: "劣势路",
    4: "打野",
}

POSITION_NAMES = {
    1: "推测 Pos 1",
    2: "推测 Pos 2",
    3: "推测 Pos 3",
    4: "推测 Pos 4",
    5: "推测 Pos 5",
}

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


def _economy_score(player: Dict[str, Any]) -> int:
    net_worth = _safe_int(player.get("net_worth"))
    if net_worth:
        return net_worth
    return (
        _safe_int(player.get("gold_per_min")) * 40
        + _safe_int(player.get("last_hits")) * 35
        + _safe_int(player.get("level")) * 250
        + _safe_int(player.get("kills")) * 180
        + _safe_int(player.get("assists")) * 70
        - _safe_int(player.get("deaths")) * 120
    )


def _estimate_position_rank(player: Dict[str, Any], players: List[Dict[str, Any]]) -> int:
    player_team = _is_radiant(player.get("player_slot"))
    team = [
        entry for entry in players
        if isinstance(entry, dict) and _is_radiant(entry.get("player_slot")) == player_team
    ]
    if len(team) < 5:
        return 0

    ranked = sorted(
        team,
        key=lambda entry: (
            _economy_score(entry),
            _safe_int(entry.get("last_hits")),
            _safe_int(entry.get("gold_per_min")),
        ),
        reverse=True,
    )
    for index, entry in enumerate(ranked, start=1):
        if entry is player or _safe_int(entry.get("player_slot"), -1) == _safe_int(player.get("player_slot"), -2):
            return index
    return 0


def _role_payload(lane_role: int, position_rank: int = 0) -> Dict[str, Any]:
    lane_name = LANE_ROLE_NAMES.get(lane_role, "分路未知")
    position_name = POSITION_NAMES.get(position_rank, "定位待估算")

    if lane_role > 0 and position_rank:
        role_name = f"{lane_name} / {position_name}"
        role_source = "parsed+estimated"
    elif lane_role > 0:
        role_name = lane_name
        role_source = "parsed"
    elif position_rank:
        role_name = position_name
        role_source = "estimated"
    else:
        role_name = lane_name
        role_source = "unknown"

    return {
        "lane_role_name": lane_name,
        "position_rank": position_rank,
        "position_name": position_name,
        "role_name": role_name,
        "role_source": role_source,
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
    position_rank = _estimate_position_rank(player, players)
    kills = _safe_int(player.get("kills"))
    deaths = _safe_int(player.get("deaths"))
    assists = _safe_int(player.get("assists"))

    return match_id, {
        "detail_available": True,
        "kills": kills,
        "deaths": deaths,
        "assists": assists,
        "kda": _kda(kills, deaths, assists),
        "lane_role": lane_role,
        **_role_payload(lane_role, position_rank),
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
            "body": "近期输局里高死亡样本偏多，最该复盘的是二塔外带线和无视野开雾前的位置。",
            "action": "每局 12 分钟后死亡前 10 秒标记一次视野来源。",
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


@router.get("/players/{account_id}/dashboard")
def player_dashboard(account_id: int, limit: int = Query(50, ge=10, le=100)):
    warnings: List[str] = []

    profile_raw, warning = _cached_get(f"/players/{account_id}", timeout=10)
    if warning:
        warnings.append(warning)

    recent_raw, warning = _cached_get(f"/players/{account_id}/recentMatches", timeout=12)
    if warning:
        warnings.append(warning)

    wl_raw, warning = _cached_get(f"/players/{account_id}/wl", timeout=10)
    if warning:
        warnings.append(warning)

    heroes_raw, warning = _cached_get(f"/players/{account_id}/heroes", timeout=12)
    if warning:
        warnings.append(warning)

    ratings_raw, warning = _cached_get(f"/players/{account_id}/ratings", timeout=12)
    if warning:
        warnings.append(warning)

    counts_raw, warning = _cached_get(f"/players/{account_id}/counts", timeout=12)
    if warning:
        warnings.append(warning)

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
        "rank_history": _rank_history(ratings_raw),
        "rolling_winrate": _rolling_winrate(recent_matches),
        "time_analysis": time_data,
        "weekday_analysis": weekday_data,
        "counts": _counts_summary(counts_raw),
        "coach": _coach_pack(summary, recent_matches, hero_pool, lifetime_heroes, time_data, weekday_data),
        "warnings": warnings,
        "updated_at": datetime.now(tz=CN_TZ).strftime("%Y-%m-%d %H:%M:%S"),
    }
