"""Quick hero reference: Valve mechanics and verified Immortal players' builds."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from html.parser import HTMLParser
from statistics import median
from threading import Lock
import re
import time

import requests
from fastapi import APIRouter, HTTPException, Path

from fetch_dota_stats import HEROES_CN, HEROES_EN, get_hero_icon_url
from routers.players import _cached_get, _safe_int

router = APIRouter()
VALVE_URL = "https://www.dota2.com/datafeed"
CDN = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react"
SAMPLE_LIMIT = 8
PLAYER_LIMIT = 8
WINDOW_DAYS = 14
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


def aggregate_builds(hero_id, details, catalog, ranked_players=None, now=None):
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
            "player": (rank or {}).get("profile", {}).get("name") or (rank or {}).get("profile", {}).get("personaname") or player.get("name") or player.get("personaname") or f"玩家 {player.get('account_id') or '匿名'}",
            "match_type": "天梯排位" if detail.get("lobby_type") == 7 else (detail.get("league") or {}).get("name") or "比赛类型未核验", "win": win,
            "account_id": player.get("account_id"), "rank_tier": rank.get("rank_tier") if rank else None,
            "leaderboard_rank": rank.get("leaderboard_rank") if rank else None,
            "rank_checked_at": rank.get("checked_at") if rank else None,
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
            "context": ITEM_CONTEXT.get(slug, "这是本批样本常见的成装。结合你的职责、敌方阵容和当前经济再选择。"),
        })
    return {"candidates": candidates, "matches": matches, "sample": len(rows), "patch_id": patch}


@router.get("/hero-guides/{hero_id}/builds")
def hero_builds(hero_id: int = Path(ge=1, le=2000)):
    key = f"ranked_builds:{hero_id}"
    cached = _cache.get(key)
    if cached and time.time() - cached["time"] < cached["ttl"]:
        return cached["data"]
    with _lock(key):
        cached = _cache.get(key)
        if cached and time.time() - cached["time"] < cached["ttl"]:
            return cached["data"]
        now = int(time.time())
        with ThreadPoolExecutor(max_workers=4) as pool:
            # League appearances find recently active accounts; they never enter
            # the ranked inventory sample or establish a player's rank.
            recent_future = pool.submit(_public_get, f"/heroes/{hero_id}/matches", timeout=10, attempts=1)
            rankings_future = pool.submit(_public_get, "/rankings", {"hero_id": hero_id}, timeout=10, attempts=1)
            catalog_future = pool.submit(_public_get, "/constants/items", timeout=10, attempts=1)
            patch_future = pool.submit(_public_get, "/constants/patch", timeout=10, attempts=1)
            recent, recent_warning = recent_future.result()
            rankings, rankings_warning = rankings_future.result()
            active = [row for row in recent if isinstance(row, dict) and row.get("leagueid") and
                      now - WINDOW_DAYS * 86400 <= _safe_int(row.get("start_time")) <= now] if isinstance(recent, list) else []
            active.sort(key=lambda row: row["start_time"], reverse=True)
            leaders = rankings.get("rankings", []) if isinstance(rankings, dict) and isinstance(rankings.get("rankings"), list) else []
            account_ids = list(dict.fromkeys(row["account_id"] for row in [*active, *leaders]
                                            if isinstance(row, dict) and type(row.get("account_id")) is int and row["account_id"] > 0))[:PLAYER_LIMIT]
            rank_futures = {account_id: pool.submit(_public_get, f"/players/{account_id}", timeout=10, attempts=1) for account_id in account_ids}
            ranks, rank_warning = {}, False
            for account_id, future in rank_futures.items():
                profile, warning = future.result()
                rank_warning = rank_warning or bool(warning)
                if not warning and _verified_rank(profile, account_id):
                    ranks[account_id] = {**profile, "checked_at": int(time.time())}
            params = {"hero_id": hero_id, "lobby_type": 7, "date": WINDOW_DAYS, "limit": 4}
            history_futures = {account_id: pool.submit(_public_get, f"/players/{account_id}/matches", params, timeout=10, attempts=1) for account_id in ranks}
            eligible, history_warning = {}, False
            for account_id, future in history_futures.items():
                history, warning = future.result()
                history_warning = history_warning or bool(warning)
                for row in history if isinstance(history, list) else []:
                    if _recent_ranked(row, hero_id, now):
                        eligible.setdefault(str(row["match_id"]), {**row, "expected_account_id": account_id})
            selected = sorted(eligible.values(), key=lambda row: row["start_time"], reverse=True)[:SAMPLE_LIMIT]
            futures = [pool.submit(_public_get, f"/matches/{row['match_id']}", timeout=10, attempts=1) for row in selected]
            results = [future.result() for future in futures]
            details = [data for row, (data, _) in zip(selected, results) if isinstance(data, dict) and
                       str(data.get("match_id")) == str(row["match_id"]) and any(
                           isinstance(player, dict) and player.get("hero_id") == hero_id and
                           player.get("account_id") == row["expected_account_id"] for player in data.get("players") or [])]
            detail_warning = any(warning for _, warning in results)
            catalog_raw, catalog_warning = catalog_future.result()
            patches, patch_warning = patch_future.result()
        payload = aggregate_builds(hero_id, details, _catalog(catalog_raw), ranks, now)
        patch = next((patch for patch in (patches if isinstance(patches, list) else []) if isinstance(patch, dict) and patch.get("id") == payload["patch_id"]), None)
        payload["patch_name"] = patch.get("name") if patch else None
        used = {match["account_id"] for match in payload["matches"]}
        players = [{"account_id": account_id, "name": rank["profile"].get("name") or rank["profile"].get("personaname") or str(account_id),
                    "rank_tier": rank["rank_tier"], "leaderboard_rank": rank["leaderboard_rank"], "checked_at": rank["checked_at"],
                    "url": f"https://www.opendota.com/players/{account_id}"} for account_id, rank in ranks.items() if account_id in used]
        warned = bool(recent_warning or rankings_warning or rank_warning or history_warning or detail_warning or catalog_warning or patch_warning)
        status = "unavailable" if warned and not payload["sample"] else "insufficient" if payload["sample"] < 3 else "partial" if warned or payload["sample"] < len(selected) else "ready"
        payload["source"] = {"label": "OpenDota 冠绝选手近期天梯", "url": "https://docs.opendota.com/#tag/players",
                             "scope": "ranked_immortal_players", "fetched_at": now, "window_days": WINDOW_DAYS,
                             "attempted": len(selected), "players_checked": len(account_ids), "players_verified": len(ranks),
                             "players": players, "position_verified": False, "status": status}
        _cache[key] = {"data": payload, "time": now, "ttl": 600 if payload["sample"] >= 3 else 60}
        return payload
