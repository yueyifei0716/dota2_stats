"""Quick hero reference: Valve mechanics and verified Immortal players' builds."""

import gzip
import json
from pathlib import Path as FilesystemPath

from collections import Counter
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from html.parser import HTMLParser
from statistics import median
from threading import Lock
from pathlib import Path as FilePath
import json
import os
import re
import tempfile
import time

import requests
from urllib3.util import Timeout
from fastapi import APIRouter, HTTPException, Path

from fetch_dota_stats import HEROES_CN, HEROES_EN, get_hero_icon_url
from routers.players import _cached_get, _safe_int
from services.hero_tips import usage_tips
from services.hero_playbooks import operating_guide

router = APIRouter()
VALVE_URL = "https://www.dota2.com/datafeed"
CDN = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react"
SAMPLE_LIMIT = 24
PLAYER_LIMIT = 12
HISTORY_LIMIT = 8
REQUEST_LIMIT = 4 + PLAYER_LIMIT * 2 + SAMPLE_LIMIT
PUBLIC_FEED_PAGES = 2
DISCOVERY_DETAIL_LIMIT = 4
BUILD_EVIDENCE_MAX_AGE = 86400
BUILD_CACHE_DIR = FilePath(tempfile.gettempdir()) / "dota2stats-verified-hero-builds-v1"
BUILD_SNAPSHOT_DIR = FilePath(__file__).resolve().parents[1] / "snapshots" / "hero_builds"
WINDOW_DAYS = 14
BUILD_BUDGET_SECONDS = 22
RANKED_MODES = {1, 2, 3, 4, 16, 22}
_cache = {}
_locks = {}
_guard = Lock()


def _lock(key):
    with _guard:
        return _locks.setdefault(key, Lock())


def _valve(kind, hero_id=None):
    key = (kind, hero_id)
    cached = _cache.get(key)
    if not cached:
        snapshot_key = "bundled_valve_public"
        snapshot = _cache.get(snapshot_key)
        if not snapshot:
            try:
                snapshot = json.loads(gzip.decompress((FilesystemPath(__file__).resolve().parents[1] / "snapshots/valve_public.json.gz").read_bytes()))
                if (not isinstance(snapshot.get("heroes"), list) or
                        not 0 <= time.time() - snapshot.get("fetched_at", 0) < 86400):
                    snapshot = None
                if snapshot:
                    _cache[snapshot_key] = snapshot
            except (OSError, ValueError, TypeError):
                snapshot = None
        if snapshot and 0 <= time.time() - snapshot.get("fetched_at", 0) < 86400:
            heroes = [hero for hero in snapshot["heroes"] if hero_id is None or hero.get("id") == hero_id]
            if heroes:
                cached = {"data": {"heroes":heroes}, "time": snapshot["fetched_at"]}
                _cache[key] = cached
    if cached and time.time() - cached["time"] < 86400:
        return cached["data"], cached["time"], False
    with _lock(str(key)):
        cached = _cache.get(key)
        if cached and time.time() - cached["time"] < 86400:
            return cached["data"], cached["time"], False
        try:
            params = {"language": "schinese"}
            if hero_id is not None:
                params["hero_id"] = hero_id
            response = requests.get(f"{VALVE_URL}/{kind}", params=params, timeout=10)
            response.raise_for_status()
            data = response.json().get("result", {}).get("data", {})
            if not isinstance(data.get("heroes"), list) or not data["heroes"]:
                raise ValueError("Missing hero data")
            fetched = time.time()
            _cache[key] = {"data": data, "time": fetched}
            return data, fetched, False
        except (requests.RequestException, ValueError, AttributeError):
            if cached:
                return cached["data"], cached["time"], True
            return {}, None, True


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in {"br", "p"}:
            self.parts.append(" ")


def _description(raw, ability, variant="base"):
    values = {}
    for field in ability.get("special_values", []):
        if not isinstance(field, dict):
            continue
        numbers = field.get(f"values_{variant}") if variant != "base" else None
        numbers = numbers or field.get("values_float") or []
        if numbers:
            values[field.get("name")] = "/".join(f"{number:g}" for number in numbers if isinstance(number, (int, float)))
    substituted = re.sub(r"%([a-zA-Z_0-9]+)%", lambda match: values.get(match[1], "对应数值"), str(raw or ""))
    parser = _PlainText()
    parser.feed(unescape(substituted))
    return " ".join("".join(parser.parts).split()).replace("%%", "%")


@router.get("/hero-guides/heroes")
def guide_heroes():
    data, fetched, stale = _valve("herolist")
    heroes = [{
        "hero_id": hero["id"], "hero_cn": hero.get("name_loc", ""),
        "hero_en": hero.get("name_english_loc", ""),
        "hero_icon": f"{CDN}/heroes/{hero['name'].removeprefix('npc_dota_hero_')}.png",
    } for hero in data.get("heroes", []) if hero.get("id") and hero.get("name")]
    source = "Valve"
    if not heroes:
        source = "内置英雄目录"
        heroes = [{"hero_id": hero_id, "hero_cn": name, "hero_en": HEROES_EN.get(hero_id, ""), "hero_icon": get_hero_icon_url(hero_id)} for hero_id, name in HEROES_CN.items()]
    return {"heroes": heroes, "source": source, "fetched_at": fetched, "stale": stale}


# These are practice sequences, not measured optimal combos. Required skills must
# still exist in the current Valve response before a sequence is published.
PRACTICE = {
    7: {
        "title": "跳刀切入，衔接余震控制", "skills": ["earthshaker_echo_slam", "earthshaker_enchant_totem", "earthshaker_fissure", "earthshaker_aftershock"],
        "steps": ["blink", "earthshaker_echo_slam", "earthshaker_enchant_totem", "attack", "earthshaker_fissure"],
        "use_when": "敌人聚在一起、队友能接上输出时，从视野外切入。",
        "watch_out": "余震来自施放技能，使用物品不会触发。控制要接续，避免把眩晕全重叠；沟壑也可能挡住队友。",
    },
    2: {
        "title": "跳刀吼住，再用刃甲接伤害", "skills": ["axe_berserkers_call", "axe_culling_blade"],
        "steps": ["blink", "axe_berserkers_call", "blade_mail", "axe_culling_blade"],
        "use_when": "对方输出英雄聚在一起，并且你的队友能及时跟进。",
        "watch_out": "淘汰之刃要确认击杀阈值；切入前预留吼和斩的魔法。刃甲开启时机取决于敌人的攻击节奏。",
    },
    26: {
        "title": "先羊住，再衔接穿刺", "skills": ["lion_voodoo", "lion_impale", "lion_finger_of_death"],
        "steps": ["blink", "lion_voodoo", "lion_impale", "lion_finger_of_death"],
        "use_when": "需要优先限制一个有逃生技能的目标，并让队友跟进。",
        "watch_out": "先确认林肯等抵挡效果；不要把两个控制全重叠。死亡之指用于能完成击杀的目标。",
    },
    97: {
        "title": "跳刀大招，把目标带向队友", "skills": ["magnataur_reverse_polarity", "magnataur_skewer"],
        "steps": ["blink", "magnataur_reverse_polarity", "magnataur_skewer"],
        "use_when": "敌人集中、队友在你准备拖回的方向时。",
        "watch_out": "先看队友位置和拖拽路线，别把目标带出队友伤害范围。具体施法范围按当前技能等级查看。",
    },
    104: {
        "title": "决斗前先把自我强化开好", "skills": ["legion_commander_press_the_attack", "legion_commander_duel"],
        "steps": ["legion_commander_press_the_attack", "blade_mail", "blink", "legion_commander_duel"],
        "use_when": "队友已经就位，可以共同完成决斗击杀。",
        "watch_out": "先确认救人技能、伤害和视野；不要只为了开始决斗而切进敌人全队。刃甲是情境选择，不是必需条件。",
    },
    76: {
        "title": "禁锢限制目标，再接神智之蚀", "skills": ["obsidian_destroyer_astral_imprisonment", "obsidian_destroyer_sanity_eclipse"],
        "steps": ["obsidian_destroyer_astral_imprisonment", "obsidian_destroyer_sanity_eclipse"],
        "use_when": "需要先限制一个关键目标，并且最大魔法值差足以支持大招伤害时。",
        "watch_out": "神智之蚀能命中星体禁锢里的单位；但普通攻击和其他队友技能不能照常命中隐藏目标，别让跟进伤害打空。禁锢也能用于保护队友。",
    },
}


def _abilities(hero):
    result = []
    for ability in hero.get("abilities", []):
        if not isinstance(ability, dict) or not ability.get("name") or not ability.get("name_loc") or ability.get("is_item"):
            continue
        behavior = _safe_int(ability.get("behavior"))
        kind = "先天" if ability.get("ability_is_innate") else "被动" if behavior & 2 else "持续施法" if behavior & 128 else "主动"
        result.append({
            "id": ability.get("id"), "slug": ability["name"], "name": ability["name_loc"],
            "icon": f"{CDN}/abilities/{ability['name']}.png", "kind": kind,
            "description": _description(ability.get("desc_loc"), ability),
            "notes": [_description(note, ability) for note in ability.get("notes_loc", [])][:3],
            "scepter": _description(ability.get("scepter_loc"), ability, "scepter"),
            "shard": _description(ability.get("shard_loc"), ability, "shard"),
            "cooldowns": ability.get("cooldowns", []), "mana_costs": ability.get("mana_costs", []),
        })
    return result


@router.get("/hero-guides/{hero_id}")
def hero_mechanics(hero_id: int = Path(ge=1, le=2000)):
    data, fetched, stale = _valve("herodata", hero_id)
    hero = next((hero for hero in data.get("heroes", []) if hero.get("id") == hero_id), None)
    if not hero:
        available = bool(data.get("heroes"))
        raise HTTPException(404 if available else 503, "没有找到这个英雄" if available else "英雄技能资料暂时不可用")
    abilities = _abilities(hero)
    slugs = {ability["slug"] for ability in abilities}
    practice = PRACTICE.get(hero_id)
    if practice and not set(practice["skills"]).issubset(slugs):
        practice = None
    return {
        "hero": {"hero_id": hero_id, "hero_cn": hero.get("name_loc"), "hero_en": HEROES_EN.get(hero_id, ""), "hero_icon": f"{CDN}/heroes/{hero['name'].removeprefix('npc_dota_hero_')}.png"},
        "summary": _description(hero.get("npe_desc_loc") or hero.get("hype_loc"), {}),
        "abilities": abilities, "practice": practice,
        "usage_tips": usage_tips(hero, abilities) if not stale else [],
        "operating_guide": operating_guide(hero, abilities) if not stale else None,
        "source": {"label": "Valve 官方中文技能资料", "url": f"{VALVE_URL}/herodata?language=schinese&hero_id={hero_id}", "fetched_at": fetched, "stale": stale},
    }


BLINK_FAMILY = {"overwhelming_blink", "swift_blink", "arcane_blink"}
BOOTS = {"boots", "power_treads", "phase_boots", "arcane_boots", "tranquil_boots", "travel_boots", "travel_boots_2", "boots_of_bearing", "guardian_greaves"}
ITEM_CONTEXT = {
    "blink": "需要近距离先手或切入后排时考虑。提前藏住视野，避开会持续打断跳刀的伤害。",
    "blade_mail": "敌人必须攻击你、或你能主动逼对手交伤害时考虑。开启时机比无脑常开更重要。",
    "black_king_bar": "对方控制或法术让你无法完整输出时考虑。切入前确认哪些技能仍能限制你。",
    "force_staff": "需要救队友、脱离贴身或调整站位时考虑。推行方向取决于目标朝向。",
    "glimmer_cape": "需要保护被集火的队友时考虑；敌方真视会影响隐身带来的价值。",
    "sphere": "对方关键单体技能容易直接打断你的计划时考虑；先确认敌人能否轻易破掉抵挡。",
    "sheepstick": "需要稳定限制一个关键目标、给队友跟伤害时考虑。",
    "aghanims_scepter": "先看下方对应技能的神杖变化，再判断是否解决这局的核心问题。",
    "ultimate_scepter": "先看下方对应技能的神杖变化，再判断是否解决这局的核心问题。",
    "hurricane_pike": "需要攻击距离和脱离近身的空间时考虑。",
    "yasha_and_kaya": "需要兼顾机动性和法术输出，并且已有稳定施法空间时考虑。不要因此延后这局更急需的生存装备。",
    "pipe": "团队承受大量法术伤害，需要共同防护时考虑。",
    "lotus_orb": "需要驱散或处理针对队友的单体法术时考虑；反弹不代表原法术失效。",
}


def _catalog(data):
    return {item["id"]: {**item, "slug": slug} for slug, item in (data if isinstance(data, dict) else {}).items() if isinstance(item, dict) and isinstance(item.get("id"), int)}


def _item(item_id, catalog):
    raw = catalog.get(item_id, {})
    slug = raw.get("slug", "")
    return {"item_id": item_id, "slug": slug, "name": raw.get("dname") or ("装备未记录" if item_id is None else f"物品 #{item_id}" if item_id else ""), "icon": f"{CDN}/items/{slug}.png" if slug else "", "cost": raw.get("cost")}


def _candidate(slug, catalog_by_slug):
    item = catalog_by_slug.get(slug, {})
    return bool(item and not slug.startswith("recipe_") and slug not in BOOTS and
                _safe_int(item.get("cost")) >= 1800 and (item.get("created") or slug == "blink"))


def _verified_rank(profile, account_id):
    if not isinstance(profile, dict) or not isinstance(profile.get("profile"), dict):
        return False
    rank, leaderboard = profile.get("rank_tier"), profile.get("leaderboard_rank")
    return (profile["profile"].get("account_id") == account_id and
            type(rank) is int and rank == 80 and type(leaderboard) is int and leaderboard > 0)


def _recent_ranked(match, hero_id, now):
    return (isinstance(match, dict) and match.get("hero_id") == hero_id and match.get("lobby_type") == 7 and
            match.get("game_mode") in RANKED_MODES and isinstance(match.get("start_time"), (int, float)) and
            now - WINDOW_DAYS * 86400 <= match["start_time"] <= now and
            isinstance(match.get("duration"), (int, float)) and match["duration"] > 0 and match.get("match_id"))


def _public_get(path, params=None, **options):
    # Disable the shared client's key injection; requests omits None parameters.
    return _cached_get(path, {**(params or {}), "api_key": None}, **options)


LANE_NAMES = {1: "优势路", 2: "中路", 3: "劣势路", 4: "打野"}


def _lane(player):
    value = player.get("lane_role")
    return value if type(value) is int and value in LANE_NAMES else None


def _purchase_sequence(player, duration, catalog_by_slug):
    """Completed items observed in the replay; inventory never supplies order."""
    events = []
    for index, purchase in enumerate(player.get("purchase_log") or []):
        if not isinstance(purchase, dict):
            continue
        slug, seconds = purchase.get("key"), purchase.get("time")
        item = catalog_by_slug.get(slug, {})
        if (not isinstance(slug, str) or slug.startswith("recipe_") or
                type(seconds) not in (int, float) or not 0 <= seconds <= duration):
            continue
        if not item:
            continue
        if (_candidate(slug, catalog_by_slug) or (slug in BOOTS and _safe_int(item.get("cost")) >= 1000) or
                slug in BLINK_FAMILY or (slug == "aghanims_shard" and item)):
            events.append((seconds, index, slug))
    events.sort()
    seen, result = set(), []
    for seconds, _, slug in events:
        if slug not in seen:
            seen.add(slug)
            result.append({**_item(catalog_by_slug[slug]["id"], {item["id"]: item for item in catalog_by_slug.values()}),
                           "time": seconds, "minute": round(seconds / 60, 1)})
    return result


def _group_stats(matches, candidates):
    logs = [match for match in matches if match["purchase_sequence"]]
    branches = {}
    purchased = {}
    for match in logs:
        for item in match["purchase_sequence"]:
            purchased.setdefault(item["slug"], []).append((match, item))
        # The first three observed major purchases define a reproducible branch;
        # this is not a complete build or a recommendation.
        prefix = tuple(item["slug"] for item in match["purchase_sequence"][:3])
        branch = branches.setdefault(prefix, {"items": match["purchase_sequence"][:3], "rows": []})
        branch["rows"].append(match)
    sequences = []
    for prefix, branch in sorted(branches.items(), key=lambda pair: (-len(pair[1]["rows"]), pair[0])):
        rows = branch["rows"]
        sequences.append({"slugs": list(prefix), "items": [{key: value for key, value in item.items() if key not in {"time", "minute"}} for item in branch["items"]],
                          "matches": len(rows), "sample": len(logs), "players": len({row["account_id"] for row in rows if row["account_id"]}),
                          "frequency": round(len(rows) / len(logs) * 100, 1), "example_matches": [row["match_id"] for row in rows[:3]],
                          "complete_prefix": len(prefix) == 3})
    lane = matches[0]["lane_role"]
    purchase_items = []
    for slug, observations in sorted(purchased.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        item = observations[0][1]
        purchase_items.append({**{key: value for key, value in item.items() if key not in {"time", "minute"}},
                               "matches": len(observations), "sample": len(logs),
                               "players_count": len({row["account_id"] for row, _ in observations if row["account_id"]}),
                               "pick_rate": round(len(observations) / len(logs) * 100, 1), "timing_sample": len(observations),
                               "purchase_minute": round(median(item["time"] for _, item in observations) / 60, 1) if len(observations) >= 3 else None,
                               "example_matches": [row["match_id"] for row, _ in observations[:3]]})
    return {"patch_id": matches[0]["patch_id"], "lane_role": lane, "lane_name": LANE_NAMES.get(lane, "分路未知"),
            "position": None, "position_verified": False, "sample": len(matches), "inventory_sample": len(matches),
            "players_count": len({match["account_id"] for match in matches if match["account_id"]}),
            "purchase_log_sample": len(logs), "missing_purchase_log_sample": len(matches) - len(logs),
            "status": "observed" if len(matches) >= 3 else "small_sample", "candidates": candidates,
            "purchase_items": purchase_items, "purchase_branches": sequences[:8], "match_ids": [match["match_id"] for match in matches],
            "purchase_note": "仅统计回放实际记录的主要购买；未解析日志不进入分母。单件中位时间不是共同购买顺序。"}


def _select_matches(eligible):
    """Give each verified account one recent game per round before repeats."""
    by_player = {}
    for row in sorted(eligible.values(), key=lambda row: row["start_time"], reverse=True):
        by_player.setdefault(row["expected_account_id"], []).append(row)
    selected = []
    for index in range(HISTORY_LIMIT):
        round_rows = [history[index] for history in by_player.values() if len(history) > index]
        for row in sorted(round_rows, key=lambda row: row["start_time"], reverse=True):
            selected.append(row)
            if len(selected) == SAMPLE_LIMIT:
                return selected
    return selected


def _source_warning(stage, warning):
    """Expose actionable upstream failures without exception URLs or internals."""
    raw = str(warning).lower()
    status = re.search(r"http\s+(\d{3})", raw)
    code = int(status[1]) if status else None
    reason = ("rate_limited" if code == 429 else "access_denied" if code in {401, 403} else
              "http_error" if code else "budget_exhausted" if "budget exhausted" in raw else
              "timeout" if "timeout" in raw or "timed out" in raw or "超时" in raw else
              "stale_upstream_cache" if "缓存" in raw else "upstream_unavailable")
    return {"stage": stage, "reason": reason, "http_status": code}


def _public_feed(fetch, deadline):
    """Two sampled high-tier pages shared by every hero, never rank evidence.

    Official odota/core svc/api/spec.ts clamps min_rank to 75; the feed's
    average tier cannot verify an individual Immortal leaderboard account.
    """
    key = "ranked_public_feed"
    cached = _cache.get(key)
    if cached and time.time() - cached["time"] < cached["ttl"]:
        return cached["data"], cached.get("warning")
    lock = _lock(key)
    if not lock.acquire(timeout=max(0, deadline - time.monotonic())):
        return [], "upstream request budget exhausted"
    try:
        cached = _cache.get(key)
        if cached and time.time() - cached["time"] < cached["ttl"]:
            return cached["data"], cached.get("warning")
        rows, warning, pages = [], None, 0
        params = {"min_rank": 75}
        for _ in range(PUBLIC_FEED_PAGES):
            page, page_warning = fetch("/publicMatches", params, timeout=8, attempts=1)
            pages += 1
            if page_warning or not isinstance(page, list):
                warning = page_warning or "invalid public feed response"
                break
            rows.extend(row for row in page if isinstance(row, dict))
            ids = [row["match_id"] for row in page if isinstance(row, dict) and type(row.get("match_id")) is int and row["match_id"] > 0]
            if not ids or len(page) < 100:
                break
            cursor = min(ids)
            if params.get("less_than_match_id") is not None and cursor >= params["less_than_match_id"]:
                break
            params = {"min_rank": 75, "less_than_match_id": cursor}
        if warning and not rows and cached:
            rows = cached["data"]
        _cache[key] = {"data": rows, "warning": warning, "time": time.time(), "ttl": 60 if warning else 600, "pages": pages}
        return rows, warning
    finally:
        lock.release()


def _valid_saved_build(hero_id, payload, now):
    """A stored snapshot is past public evidence, never a fresh rank check."""
    if not isinstance(payload, dict):
        return False
    source, matches, groups = payload.get("source"), payload.get("matches"), payload.get("groups")
    if not isinstance(source, dict) or source.get("scope") != "ranked_immortal_players":
        return False
    fetched = source.get("fetched_at")
    if type(fetched) not in (int, float) or not 0 <= now - fetched <= BUILD_EVIDENCE_MAX_AGE:
        return False
    if not isinstance(matches, list) or not matches or len(matches) != payload.get("sample") or len(matches) > SAMPLE_LIMIT:
        return False
    players = source.get("players")
    if not isinstance(players, list) or any(not isinstance(player, dict) for player in players):
        return False
    ranks = {player.get("account_id"): player for player in players if type(player.get("account_id")) is int}
    if len(ranks) != len(players):
        return False
    seen = set()
    for match in matches:
        if not isinstance(match, dict):
            return False
        match_id, account = match.get("match_id"), match.get("account_id")
        if (not isinstance(match_id, str) or not match_id.isdecimal() or int(match_id) <= 0 or match_id in seen or
                type(account) is not int or account <= 0 or match.get("hero_id") != hero_id or
                type(match.get("hero_id")) is not int or type(match.get("lobby_type")) is not int or type(match.get("game_mode")) is not int or
                match.get("lobby_type") != 7 or match.get("game_mode") not in RANKED_MODES or
                match.get("patch_id") != payload.get("patch_id") or match.get("position") is not None):
            return False
        seen.add(match_id)
        checked = match.get("rank_checked_at")
        rank = ranks.get(account, {})
        if (type(checked) not in (int, float) or not 0 <= now - checked <= BUILD_EVIDENCE_MAX_AGE or
                type(match.get("rank_tier")) is not int or match["rank_tier"] != 80 or
                type(match.get("leaderboard_rank")) is not int or match["leaderboard_rank"] <= 0 or
                rank.get("rank_tier") != match["rank_tier"] or rank.get("leaderboard_rank") != match["leaderboard_rank"] or
                type(rank.get("rank_tier")) is not int or type(rank.get("leaderboard_rank")) is not int or
                rank.get("checked_at") != checked or not _recent_ranked(match, hero_id, now)):
            return False
        items = match.get("items")
        if not isinstance(items, list) or len(items) != 6 or any(not isinstance(item, dict) or type(item.get("item_id")) is not int or item["item_id"] < 0 for item in items):
            return False
        sequence = match.get("purchase_sequence")
        if (not isinstance(sequence, list) or any(not isinstance(item, dict) or not isinstance(item.get("slug"), str) or
                type(item.get("time")) not in (int, float) or not 0 <= item["time"] <= match["duration"] for item in sequence)):
            return False
    if set(ranks) != {match["account_id"] for match in matches} or not isinstance(groups, list) or not groups:
        return False
    covered = []
    for group in groups:
        if not isinstance(group, dict) or group.get("patch_id") != payload.get("patch_id"):
            return False
        if (not isinstance(group.get("candidates"), list) or any(not isinstance(item, dict) for item in group["candidates"]) or
                (group.get("lane_role") is not None and (type(group["lane_role"]) is not int or group["lane_role"] not in LANE_NAMES))):
            return False
        ids = group.get("match_ids")
        if not isinstance(ids, list) or not ids or any(not isinstance(match_id, str) for match_id in ids) or len(set(ids)) != len(ids):
            return False
        subset = [match for match in matches if match["match_id"] in ids]
        if (len(subset) != len(ids) or any(match.get("lane_role") != group.get("lane_role") for match in subset) or
                group.get("position") is not None or group.get("position_verified") is not False):
            return False
        if group != _group_stats(subset, group.get("candidates", [])):
            return False
        covered.extend(ids)
    return len(covered) == len(seen) and set(covered) == seen


def _read_saved_build(directory, hero_id, now):
    if type(hero_id) is not int or not 1 <= hero_id <= 2000:
        return None
    try:
        path = directory / f"{hero_id}.json"
        if path.stat().st_size > 4 * 1024 * 1024:
            return None
        record = json.loads(path.read_text())
        if (not isinstance(record, dict) or record.get("schema_version") != 1 or
                type(record.get("hero_id")) is not int or record["hero_id"] != hero_id):
            return None
        payload = record.get("payload")
        return payload if _valid_saved_build(hero_id, payload, now) else None
    except (OSError, ValueError, TypeError):
        return None


def _cacheable_build(payload):
    stored = deepcopy(payload)
    # Persist only the newest patch: every group's match must be available in
    # the compatibility match list for independent validation on the next run.
    stored["groups"] = [group for group in stored.get("groups", []) if group.get("patch_id") == stored.get("patch_id")]
    return stored


def _write_saved_build(hero_id, payload, now):
    stored = _cacheable_build(payload)
    if not _valid_saved_build(hero_id, stored, now) or stored["source"].get("stale"):
        return
    temporary = None
    try:
        BUILD_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", prefix=f"{hero_id}-", suffix=".json", dir=BUILD_CACHE_DIR, delete=False) as output:
            temporary = output.name
            json.dump({"schema_version": 1, "hero_id": hero_id, "payload": stored}, output, ensure_ascii=False)
        os.replace(temporary, BUILD_CACHE_DIR / f"{hero_id}.json")
    except (OSError, TypeError, ValueError):
        pass
    finally:
        if temporary:
            try:
                FilePath(temporary).unlink(missing_ok=True)
            except OSError:
                pass


def _build_fallback(hero_id, previous, now):
    options = []
    if isinstance(previous, dict) and previous.get("sample"):
        previous = _cacheable_build(previous)
        if _valid_saved_build(hero_id, previous, now):
            options.append((previous, "memory_cache"))
    for directory, label in ((BUILD_CACHE_DIR, "disk_cache"), (BUILD_SNAPSHOT_DIR, "bundled_public_snapshot")):
        saved = _read_saved_build(directory, hero_id, now)
        if saved:
            options.append((saved, label))
    return max(options, key=lambda option: option[0]["source"]["fetched_at"]) if options else (None, None)


def aggregate_builds(hero_id, details, catalog, ranked_players=None, now=None, _grouped=False):
    now = time.time() if now is None else now
    rows = []
    seen = set()
    for detail in details:
        if not isinstance(detail, dict) or not detail.get("match_id") or detail["match_id"] in seen or not isinstance(detail.get("start_time"), (int, float)) or detail["start_time"] <= 0:
            continue
        seen.add(detail["match_id"])
        player = next((player for player in detail.get("players") or [] if isinstance(player, dict) and player.get("hero_id") == hero_id), None)
        if not player or not all(isinstance(player.get(f"item_{index}"), int) and player[f"item_{index}"] >= 0 for index in range(6)):
            continue
        evidence = (ranked_players or {}).get(player.get("account_id"))
        if ranked_players is not None and (not evidence or not _verified_rank(evidence, player.get("account_id")) or
                                          not _recent_ranked({**detail, "hero_id": player["hero_id"]}, hero_id, now)):
            continue
        slot = player.get("player_slot")
        win = (slot < 128) == detail["radiant_win"] if isinstance(slot, int) and slot in {0, 1, 2, 3, 4, 128, 129, 130, 131, 132} and isinstance(detail.get("radiant_win"), bool) else None
        rows.append({"detail": detail, "player": player, "win": win, "rank": evidence})
    rows.sort(key=lambda row: row["detail"]["start_time"], reverse=True)
    all_rows = rows
    patch = rows[0]["detail"].get("patch") if rows else None
    rows = [row for row in rows if row["detail"].get("patch") == patch]
    by_slug = {item["slug"]: item for item in catalog.values()}
    counts, wins, outcomes, timings, examples = Counter(), Counter(), Counter(), {}, {}
    matches = []
    for row in rows:
        detail, player, win, rank = row["detail"], row["player"], row["win"], row["rank"]
        items = [_item(player[f"item_{index}"], catalog) for index in range(6)]
        held = {"blink" if item["slug"] in BLINK_FAMILY else item["slug"] for item in items}
        held = {slug for slug in held if _candidate(slug, by_slug)}
        for slug in held:
            counts[slug] += 1
            if win is not None:
                outcomes[slug] += 1
                wins[slug] += int(win)
            examples.setdefault(slug, []).append(str(detail["match_id"]))
        purchases = {}
        for purchase in player.get("purchase_log") or []:
            if not isinstance(purchase, dict):
                continue
            slug, seconds = purchase.get("key"), purchase.get("time")
            if slug in BLINK_FAMILY:
                continue
            if slug in held and isinstance(seconds, (int, float)) and 0 <= seconds <= detail.get("duration", 0):
                purchases[slug] = min(seconds, purchases.get(slug, seconds))
        for slug, seconds in purchases.items():
            timings.setdefault(slug, []).append(seconds)
        matches.append({
            "match_id": str(detail["match_id"]), "start_time": detail["start_time"], "duration": detail.get("duration"),
            "hero_id": hero_id, "lobby_type": detail.get("lobby_type"), "game_mode": detail.get("game_mode"),
            "player": (rank or {}).get("profile", {}).get("name") or (rank or {}).get("profile", {}).get("personaname") or player.get("name") or player.get("personaname") or f"玩家 {player.get('account_id') or '匿名'}",
            "match_type": "天梯排位" if detail.get("lobby_type") == 7 else (detail.get("league") or {}).get("name") or "比赛类型未核验", "win": win,
            "account_id": player.get("account_id"), "rank_tier": rank.get("rank_tier") if rank else None,
            "leaderboard_rank": rank.get("leaderboard_rank") if rank else None,
            "rank_checked_at": rank.get("checked_at") if rank else None,
            "patch_id": detail.get("patch"), "lane_role": _lane(player),
            "lane_name": LANE_NAMES.get(_lane(player), "分路未知"), "position": None,
            "purchase_sequence": _purchase_sequence(player, detail["duration"], by_slug),
            "kills": player.get("kills"), "deaths": player.get("deaths"), "assists": player.get("assists"),
            "items": items, "neutral": _item(player.get("item_neutral") if isinstance(player.get("item_neutral"), int) else None, catalog),
        })
    ranked = sorted(counts, key=lambda slug: (-counts[slug], _safe_int(by_slug[slug].get("cost")), slug))
    candidates = []
    for slug in ranked[:2] if len(rows) >= 3 else []:
        raw = by_slug[slug]
        times = timings.get(slug, [])
        candidates.append({**_item(raw["id"], catalog), "matches": counts[slug], "sample": len(rows),
            "pick_rate": round(counts[slug] / len(rows) * 100, 1),
            "win_rate": round(wins[slug] / outcomes[slug] * 100, 1) if outcomes[slug] >= 3 else None,
            "purchase_minute": round(median(times) / 60, 1) if len(times) >= 3 else None,
            "timing_sample": len(times), "example_matches": examples[slug][:3],
            "outcome_sample": outcomes[slug],
            "players_count": len({row["account_id"] for row in matches if row["match_id"] in examples[slug] and row["account_id"]}),
            "context": ITEM_CONTEXT.get(slug, "这是本批样本常见的成装。结合你的职责、敌方阵容和当前经济再选择。"),
        })
    result = {"candidates": candidates, "matches": matches, "sample": len(rows), "patch_id": patch}
    if not _grouped:
        grouped = {}
        for row in all_rows:
            grouped.setdefault((row["detail"].get("patch"), _lane(row["player"])), []).append(row["detail"])
        groups = []
        for (patch_id, lane), group_details in grouped.items():
            subset = aggregate_builds(hero_id, group_details, catalog, ranked_players, now, _grouped=True)
            groups.append(_group_stats(subset["matches"], subset["candidates"]))
        groups.sort(key=lambda group: (group["patch_id"] != patch, -group["sample"], group["lane_role"] or 0))
        primary = next((group for group in groups if group["patch_id"] == patch), None)
        result.update(groups=groups, primary_lane_role=primary["lane_role"] if primary else None,
                      candidates=primary["candidates"] if primary else [],
                      players_count=len({match["account_id"] for match in matches if match["account_id"]}),
                      purchase_log_sample=sum(bool(match["purchase_sequence"]) for match in matches),
                      candidate_scope="latest_patch_primary_lane", sequence_basis="first_three_observed_major_purchases")
    return result


@router.get("/hero-guides/{hero_id}/builds")
def hero_builds(hero_id: int = Path(ge=1, le=2000)):
    key = f"ranked_builds:{hero_id}"
    def usable_cache(entry):
        if not entry or time.time() - entry["time"] >= entry["ttl"]:
            return False
        data = entry["data"]
        current = time.time()
        if data.get("sample", 0) > 0:
            fetched = data.get("source", {}).get("fetched_at")
            checked = [match.get("rank_checked_at") for match in data.get("matches", [])]
            if (type(fetched) not in (int, float) or not 0 <= current - fetched <= BUILD_EVIDENCE_MAX_AGE or
                    any(type(stamp) not in (int, float) or not 0 <= current - stamp <= BUILD_EVIDENCE_MAX_AGE for stamp in checked)):
                return False
        return not data.get("source", {}).get("stale") or _valid_saved_build(hero_id, data, current)
    cached = _cache.get(key)
    if usable_cache(cached):
        return cached["data"]
    with _lock(key):
        cached = _cache.get(key)
        if usable_cache(cached):
            return cached["data"]
        now = int(time.time())
        started = time.monotonic()
        deadline = started + BUILD_BUDGET_SECONDS
        request_guard, detail_guard = Lock(), Lock()
        request_count, next_detail_at = 0, started
        failures = []
        def warn(stage, warning):
            if warning:
                failure = _source_warning(stage, warning)
                if failure not in failures:
                    failures.append(failure)
        def fetch(path, params=None, **options):
            nonlocal request_count, next_detail_at
            with request_guard:
                if request_count >= REQUEST_LIMIT or time.monotonic() >= deadline:
                    return None, "upstream request budget exhausted"
            if path.startswith("/matches/"):
                # Keep the repository's 0.5 second match-request spacing while
                # allowing a slow response to overlap with the next request.
                with detail_guard:
                    delay = max(0, next_detail_at - time.monotonic())
                    if delay >= deadline - time.monotonic():
                        return None, "upstream request budget exhausted"
                    if delay:
                        time.sleep(delay)
                    next_detail_at = time.monotonic() + 0.5
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None, "upstream request budget exhausted"
            with request_guard:
                if request_count >= REQUEST_LIMIT:
                    return None, "upstream request budget exhausted"
                request_count += 1
            options["timeout"] = Timeout(total=remaining, connect=min(3, remaining), read=min(options.get("timeout", 10), remaining))
            return _public_get(path, params, **options)
        with ThreadPoolExecutor(max_workers=4) as pool:
            # A sampled public feed reveals current hero accounts. The average
            # tier only helps discovery; every account still needs its own
            # freshly checked Immortal rank and positive leaderboard place.
            recent_future = pool.submit(_public_feed, fetch, deadline)
            rankings_future = pool.submit(fetch, "/rankings", {"hero_id": hero_id}, timeout=10, attempts=1)
            catalog_future = pool.submit(fetch, "/constants/items", timeout=10, attempts=1)
            patch_future = pool.submit(fetch, "/constants/patch", timeout=10, attempts=1)
            recent, recent_warning = recent_future.result()
            rankings, rankings_warning = rankings_future.result()
            warn("public_feed", recent_warning)
            warn("hero_rankings", rankings_warning)
            public_candidates = [row for row in recent if isinstance(row, dict) and
                                 any(isinstance(row.get(team), list) and hero_id in row[team] for team in ("radiant_team", "dire_team")) and
                                 _recent_ranked({**row, "hero_id": hero_id}, hero_id, now)]
            public_candidates.sort(key=lambda row: row["start_time"], reverse=True)
            discovery_rows = public_candidates[:DISCOVERY_DETAIL_LIMIT]
            discovery_results = [future.result() for future in [pool.submit(fetch, f"/matches/{row['match_id']}", timeout=8, attempts=1) for row in discovery_rows]]
            active, discovered_details = [], {}
            discovery_warning = False
            for row, (detail, warning) in zip(discovery_rows, discovery_results):
                warn("public_match_discovery", warning)
                discovery_warning = discovery_warning or bool(warning)
                if not isinstance(detail, dict) or str(detail.get("match_id")) != str(row["match_id"]):
                    continue
                player = next((player for player in detail.get("players") or [] if isinstance(player, dict) and player.get("hero_id") == hero_id), None)
                if (player and type(player.get("account_id")) is int and player["account_id"] > 0 and
                        _recent_ranked({**detail, "hero_id": hero_id}, hero_id, now)):
                    active.append({"account_id": player["account_id"]})
                    discovered_details[str(detail["match_id"])] = (player["account_id"], detail)
            leaders = rankings.get("rankings", []) if isinstance(rankings, dict) and isinstance(rankings.get("rankings"), list) else []
            cursor_key = f"ranked_discovery:{hero_id}"
            cursor = _cache.get(cursor_key, {}).get("offset", 0) % max(1, len(leaders))
            discovery = (leaders[cursor:] + leaders[:cursor])[:PLAYER_LIMIT]
            # Retain successful public accounts, then explore the next bounded
            # ranking page on cache refresh instead of repeatedly checking only
            # the same inactive specialists.
            previous_players = (cached or {}).get("data", {}).get("source", {}).get("players", [])[:PLAYER_LIMIT // 2]
            account_ids = list(dict.fromkeys(row["account_id"] for row in [*previous_players, *active, *discovery]
                                            if isinstance(row, dict) and type(row.get("account_id")) is int and row["account_id"] > 0))[:PLAYER_LIMIT]
            _cache[cursor_key] = {"offset": cursor + PLAYER_LIMIT}
            rank_futures = {account_id: pool.submit(fetch, f"/players/{account_id}", timeout=10, attempts=1) for account_id in account_ids}
            ranks, rank_warning = {}, False
            for account_id, future in rank_futures.items():
                profile, warning = future.result()
                warn("rank_verification", warning)
                rank_warning = rank_warning or bool(warning)
                if not warning and _verified_rank(profile, account_id):
                    ranks[account_id] = {**profile, "checked_at": int(time.time())}
            params = {"hero_id": hero_id, "lobby_type": 7, "date": WINDOW_DAYS, "limit": HISTORY_LIMIT}
            history_futures = {account_id: pool.submit(fetch, f"/players/{account_id}/matches", params, timeout=10, attempts=1) for account_id in ranks}
            eligible = {match_id: {**detail, "hero_id": hero_id, "expected_account_id": account}
                        for match_id, (account, detail) in discovered_details.items() if account in ranks}
            history_warning = False
            for account_id, future in history_futures.items():
                history, warning = future.result()
                warn("ranked_history", warning)
                history_warning = history_warning or bool(warning)
                for row in history if isinstance(history, list) else []:
                    if (_recent_ranked(row, hero_id, now) and
                            ("account_id" not in row or row["account_id"] == account_id)):
                        eligible.setdefault(str(row["match_id"]), {**row, "expected_account_id": account_id})
            selected = _select_matches(eligible)
            def selected_detail(row):
                discovered = discovered_details.get(str(row["match_id"]))
                if discovered and discovered[0] == row["expected_account_id"]:
                    return discovered[1], None
                return fetch(f"/matches/{row['match_id']}", timeout=10, attempts=1)
            futures = [pool.submit(selected_detail, row) for row in selected]
            results = [future.result() for future in futures]
            details = [data for row, (data, _) in zip(selected, results) if isinstance(data, dict) and
                       str(data.get("match_id")) == str(row["match_id"]) and any(
                           isinstance(player, dict) and player.get("hero_id") == hero_id and
                           player.get("account_id") == row["expected_account_id"] for player in data.get("players") or [])]
            detail_warning = any(warning for _, warning in results)
            for _, warning in results:
                warn("match_details", warning)
            catalog_raw, catalog_warning = catalog_future.result()
            patches, patch_warning = patch_future.result()
            warn("item_catalog", catalog_warning)
            warn("patch_catalog", patch_warning)
        payload = aggregate_builds(hero_id, details, _catalog(catalog_raw), ranks, now)
        patch = next((patch for patch in (patches if isinstance(patches, list) else []) if isinstance(patch, dict) and patch.get("id") == payload["patch_id"]), None)
        payload["patch_name"] = patch.get("name") if patch else None
        used = {match["account_id"] for match in payload["matches"]}
        players = [{"account_id": account_id, "name": rank["profile"].get("name") or rank["profile"].get("personaname") or str(account_id),
                    "rank_tier": rank["rank_tier"], "leaderboard_rank": rank["leaderboard_rank"], "checked_at": rank["checked_at"],
                    "url": f"https://www.opendota.com/players/{account_id}"} for account_id, rank in ranks.items() if account_id in used]
        warned = bool(recent_warning or discovery_warning or rankings_warning or rank_warning or history_warning or detail_warning or catalog_warning or patch_warning)
        status = "unavailable" if warned and not payload["sample"] else "insufficient" if payload["sample"] < 3 else "partial" if warned or payload["sample"] < len(selected) else "ready"
        payload["source"] = {"label": "OpenDota 冠绝选手近期天梯", "url": "https://docs.opendota.com/#tag/players",
                             "scope": "ranked_immortal_players", "fetched_at": now, "window_days": WINDOW_DAYS,
                             "attempted": len(selected), "players_checked": len(account_ids), "players_verified": len(ranks),
                             "players": players, "position_verified": False, "status": status,
                             "elapsed_seconds": round(time.monotonic() - started, 2),
                             "budget_exhausted": time.monotonic() >= deadline,
                             "target_sample": SAMPLE_LIMIT, "request_limit": REQUEST_LIMIT, "requests_used": request_count,
                             "selection": "recent_games_round_robin_by_verified_player", "ranking_cursor": cursor,
                             "eligible_matches": len(eligible), "sample_status": "small_sample" if payload["sample"] < 20 else "observed",
                             "public_feed": {"pages": _cache.get("ranked_public_feed", {}).get("pages", 0),
                                             "rows": len(recent), "hero_candidates": len(public_candidates),
                                             "details_checked": len(discovery_rows), "accounts_discovered": len({row["account_id"] for row in active}),
                                             "min_rank": 75, "individual_rank_verified": False},
                             "warnings": failures, "stale": False,
                             "lane_basis": "OpenDota replay lane_role; not positions 1–5",
                             "purchase_basis": "replay purchase_log only; first three observed major purchases"}
        if warned and not payload["sample"]:
            saved, origin = _build_fallback(hero_id, (cached or {}).get("data", {}), now)
            if saved:
                # Original capture and rank timestamps survive cold starts and
                # repeated failed refreshes. Fallback never extends their age.
                payload = deepcopy(saved)
                payload["source"].update(status="stale", stale=True, warnings=failures, refresh_attempted_at=now,
                                         elapsed_seconds=round(time.monotonic() - started, 2),
                                         requests_used=request_count, budget_exhausted=time.monotonic() >= deadline,
                                         fallback_origin=origin, rank_reverified_on_refresh=False,
                                         freshness_note="历史公开样本，段位核验时间见原记录；本次刷新未重新核验。")
        elif payload["sample"]:
            _write_saved_build(hero_id, payload, int(time.time()))
        # Sparse but successful responses also cache for ten minutes: refreshing
        # an empty public history repeatedly cannot reveal a private history.
        _cache[key] = {"data": payload, "time": now, "ttl": 600 if not warned else 60}
        return payload
