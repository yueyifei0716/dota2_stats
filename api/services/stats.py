"""Business logic migrated from app.py: impact scores, badges, rolling winrate, time analysis, trends, role performance."""

from collections import defaultdict
from datetime import datetime, timedelta

from fetch_dota_stats import HEROES_CN, HEROES_EN

# ── Constants ──

RANK_TIERS = {
    0: "未校准",
    10: "先锋 I", 11: "先锋 I", 12: "先锋 II", 13: "先锋 III", 14: "先锋 IV", 15: "先锋 V",
    20: "卫士 I", 21: "卫士 I", 22: "卫士 II", 23: "卫士 III", 24: "卫士 IV", 25: "卫士 V",
    30: "中军 I", 31: "中军 I", 32: "中军 II", 33: "中军 III", 34: "中军 IV", 35: "中军 V",
    40: "统帅 I", 41: "统帅 I", 42: "统帅 II", 43: "统帅 III", 44: "统帅 IV", 45: "统帅 V",
    50: "传奇 I", 51: "传奇 I", 52: "传奇 II", 53: "传奇 III", 54: "传奇 IV", 55: "传奇 V",
    60: "万古流芳 I", 61: "万古流芳 I", 62: "万古流芳 II", 63: "万古流芳 III", 64: "万古流芳 IV", 65: "万古流芳 V",
    70: "超凡入圣 I", 71: "超凡入圣 I", 72: "超凡入圣 II", 73: "超凡入圣 III", 74: "超凡入圣 IV", 75: "超凡入圣 V",
    80: "冠绝一世", 81: "冠绝一世", 82: "冠绝一世", 83: "冠绝一世", 84: "冠绝一世", 85: "冠绝一世",
}

RANK_TIERS_EN = {
    0: "Uncalibrated",
    10: "Herald", 11: "Herald", 12: "Herald", 13: "Herald", 14: "Herald", 15: "Herald",
    20: "Guardian", 21: "Guardian", 22: "Guardian", 23: "Guardian", 24: "Guardian", 25: "Guardian",
    30: "Crusader", 31: "Crusader", 32: "Crusader", 33: "Crusader", 34: "Crusader", 35: "Crusader",
    40: "Archon", 41: "Archon", 42: "Archon", 43: "Archon", 44: "Archon", 45: "Archon",
    50: "Legend", 51: "Legend", 52: "Legend", 53: "Legend", 54: "Legend", 55: "Legend",
    60: "Ancient", 61: "Ancient", 62: "Ancient", 63: "Ancient", 64: "Ancient", 65: "Ancient",
    70: "Divine", 71: "Divine", 72: "Divine", 73: "Divine", 74: "Divine", 75: "Divine",
    80: "Immortal", 81: "Immortal", 82: "Immortal", 83: "Immortal", 84: "Immortal", 85: "Immortal",
}

ROLE_NAMES = {1: "优势路", 2: "中路", 3: "劣势路", 4: "辅助/游走", 5: "纯辅助"}
ROLE_SHORT = {1: "优势路", 2: "中路", 3: "劣势路", 4: "辅助", 5: "纯辅助"}

# Item ID → slug for CDN icon URL
ITEM_NAMES = {
    1: "blink", 2: "blades_of_attack", 3: "broadsword", 4: "chainmail", 5: "claymore",
    6: "helm_of_iron_will", 7: "javelin", 8: "mithril_hammer", 9: "platemail", 10: "quarterstaff",
    11: "quelling_blade", 12: "ring_of_protection", 13: "gauntlets", 14: "slippers", 15: "mantle",
    16: "branches", 17: "belt_of_strength", 18: "boots_of_elves", 19: "robe", 20: "circlet",
    21: "ogre_axe", 22: "blade_of_alacrity", 23: "staff_of_wizardry", 24: "ultimate_orb",
    25: "gloves", 26: "lifesteal", 27: "ring_of_regen", 28: "sobi_mask", 29: "boots", 30: "gem",
    31: "cloak", 32: "talisman_of_evasion", 33: "cheese", 34: "magic_stick", 36: "magic_wand",
    37: "ghost", 38: "clarity", 39: "flask", 40: "dust", 41: "bottle", 42: "ward_observer",
    43: "ward_sentry", 44: "tango", 46: "tpscroll", 48: "travel_boots", 50: "phase_boots",
    51: "demon_edge", 52: "eagle", 53: "reaver", 54: "relic", 55: "hyperstone",
    56: "ring_of_health", 57: "void_stone", 58: "mystic_staff", 59: "energy_booster",
    60: "point_booster", 61: "vitality_booster", 63: "power_treads", 65: "hand_of_midas",
    67: "oblivion_staff", 69: "pers", 73: "bracer", 75: "wraith_band", 77: "null_talisman",
    79: "mekansm", 81: "vladmir", 86: "buckler", 88: "ring_of_basilius", 90: "pipe",
    92: "urn_of_shadows", 94: "headdress", 96: "sheepstick", 98: "orchid", 100: "cyclone",
    102: "force_staff", 104: "dagon", 108: "ultimate_scepter", 110: "refresher", 112: "assault",
    114: "heart", 116: "black_king_bar", 117: "aegis", 119: "shivas_guard", 121: "bloodstone",
    123: "sphere", 125: "vanguard", 127: "blade_mail", 129: "soul_booster", 131: "hood_of_defiance",
    133: "rapier", 135: "monkey_king_bar", 137: "radiance", 139: "butterfly", 141: "greater_crit",
    143: "basher", 145: "bfury", 147: "manta", 149: "lesser_crit", 151: "armlet", 152: "invis_sword",
    154: "sange_and_yasha", 156: "satanic", 158: "mjollnir", 160: "skadi", 162: "sange",
    164: "helm_of_the_dominator", 166: "maelstrom", 168: "desolator", 170: "yasha",
    172: "mask_of_madness", 174: "diffusal_blade", 176: "ethereal_blade", 178: "soul_ring",
    180: "arcane_boots", 181: "orb_of_venom", 185: "ancient_janggo", 187: "medallion_of_courage",
    188: "smoke_of_deceit", 190: "veil_of_discord", 206: "rod_of_atos", 208: "abyssal_blade",
    210: "heavens_halberd", 214: "tranquil_boots", 215: "shadow_amulet", 216: "enchanted_mango",
    218: "ward_dispenser", 220: "travel_boots_2", 223: "meteor_hammer", 225: "nullifier",
    226: "lotus_orb", 229: "solar_crest", 231: "guardian_greaves", 232: "aether_lens",
    235: "octarine_core", 236: "dragon_lance", 237: "faerie_fire", 240: "blight_stone",
    242: "crimson_guard", 244: "wind_lace", 247: "moon_shard", 249: "silver_edge",
    250: "bloodthorn", 252: "echo_sabre", 254: "glimmer_cape", 256: "aeon_disk",
    257: "tome_of_knowledge", 259: "kaya", 260: "refresher_shard", 261: "crown",
    263: "hurricane_pike", 265: "infused_raindrop", 267: "spirit_vessel", 269: "holy_locket",
    273: "kaya_and_sange", 277: "yasha_and_kaya", 279: "ring_of_tarrasque",
    287: "keen_optic", 288: "grove_bow", 289: "quickening_charm", 290: "philosophers_stone",
    291: "force_boots", 292: "desolator_2", 297: "vampire_fangs", 298: "craggy_coat",
    299: "greater_faerie_fire", 300: "timeless_relic", 301: "mirror_shield",
    306: "pupils_gift", 309: "mind_breaker", 310: "third_eye", 311: "spell_prism", 312: "horizon",
    325: "princes_knife", 326: "spider_legs", 330: "witless_shako", 331: "vambrace",
    334: "imp_claw", 335: "flicker", 336: "spy_gadget", 349: "arcane_ring",
    354: "ocean_heart", 355: "broom_handle", 356: "trusty_shovel", 357: "nether_shawl",
    358: "dragon_scale", 359: "essence_ring", 360: "clumsy_net", 361: "enchanted_quiver",
    362: "ninja_gear", 363: "illusionsts_cape", 364: "havoc_hammer", 365: "panic_button",
    366: "apex", 367: "ballista", 368: "woodland_striders", 369: "trident", 370: "demonicon",
    371: "fallen_sky", 372: "pirate_hat", 374: "ex_machina", 375: "faded_broach",
    376: "paladin_sword", 377: "minotaur_horn", 378: "orb_of_destruction", 379: "the_leveller",
    381: "titan_sliver", 473: "voodoo_mask", 485: "blitz_knuckles", 534: "witch_blade",
    565: "chipped_vest", 569: "orb_of_corrosion", 571: "trickster_cloak", 573: "elven_tunic",
    574: "cloak_of_flames", 575: "venom_gland", 577: "possessed_mask", 578: "ancient_perseverance",
    585: "stormcrafter", 588: "overflowing_elixir", 593: "fluffy_hat", 596: "falcon_blade",
    598: "mage_slayer", 600: "overwhelming_blink", 603: "swift_blink", 604: "arcane_blink",
    609: "aghanims_shard", 610: "wind_waker", 635: "helm_of_the_overlord",
    637: "star_mace", 638: "penta_edged_sword", 674: "warhammer", 675: "psychic_headband",
    676: "ceremonial_robe", 677: "book_of_shadows", 678: "giants_ring", 679: "vengeances_shadow",
    680: "bullwhip", 686: "quicksilver_amulet", 692: "eternal_shroud",
    824: "assassins_dagger", 825: "ascetic_cap", 828: "misericorde", 829: "force_field",
    834: "black_powder_bag", 838: "unstable_wand", 908: "wraith_pact", 911: "revenants_brooch",
    931: "boots_of_bearing", 939: "harpoon", 945: "seeds_of_serenity", 946: "lance_of_pursuit",
    947: "occult_bracelet", 949: "ogre_seal_totem", 950: "defiant_shell",
    990: "eye_of_the_vizier", 1076: "specialists_array", 1077: "dagger_of_ristul",
    1091: "samurai_tabi", 1093: "hermes_sandals", 1095: "lunar_crest", 1097: "disperser",
    1100: "witches_switch", 1107: "phylactery", 1122: "diadem", 1123: "blood_grenade",
    1124: "spark_of_courage", 1125: "cornucopia", 1128: "pavise",
    1156: "ancient_guardian", 1157: "safety_bubble", 1158: "whisper_of_the_dread",
    1160: "avianas_feather", 1161: "unwavering_condition", 1167: "light_collector",
    1168: "rattlecage", 1466: "gungir", 1575: "orb_of_frost",
    1584: "enhancement_alert", 1585: "enhancement_brawny", 1586: "enhancement_tough",
    1587: "enhancement_feverish", 1588: "enhancement_fleetfooted", 1589: "enhancement_crude",
    1590: "enhancement_boundless", 1591: "enhancement_wise", 1592: "enhancement_timeless",
    1593: "enhancement_greedy", 1594: "enhancement_vampiric", 1595: "enhancement_keen_eyed",
    1596: "enhancement_evolved", 1597: "enhancement_titanic",
    1598: "unrelenting_eye", 1600: "rippers_lash", 1601: "crippling_crossbow",
    1602: "gale_guard", 1603: "gunpowder_gauntlets", 1604: "searing_signet",
    1605: "serrated_shiv", 1606: "polliwog_charm", 1607: "magnifying_monocle",
    1608: "pyrrhic_cloak", 1609: "madstone_bundle",
    1636: "crystal_raindrop", 1637: "kobold_cup", 1638: "dormant_curio",
    1639: "sisters_shroud", 1640: "jidi_pollen_bag", 1641: "outworld_staff",
    1642: "dezun_bloodrite", 1643: "giant_maul", 1644: "divine_regalia",
    1716: "weighted_dice", 1717: "ash_legion_shield", 1718: "riftshadow_prism",
    1719: "metamorphic_mandible", 1720: "idol_of_screeauk", 1721: "flayers_bota",
    1801: "caster_rapier", 1802: "tiara_of_selemene", 1803: "doubloon",
    1804: "roshans_banner", 1806: "devastator", 1808: "angels_demise",
    2096: "vindicators_axe", 2097: "duelist_gloves", 2098: "horizons_equilibrium",
    2099: "blighted_spirit", 2190: "dandelion_amulet", 2191: "turtle_shell",
    2192: "martyrs_plate", 2193: "gossamer_cape",
}


# ── Helper functions ──

def get_item_icon_url(item_id):
    """Get item icon URL from item ID."""
    if not item_id or item_id == 0 or item_id == "0":
        return ""
    try:
        item_id = int(item_id)
    except ValueError:
        return ""
    name = ITEM_NAMES.get(item_id, "")
    if name:
        return f"https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/items/{name}.png"
    return ""


def get_rank_name(rank_tier):
    """Convert rank tier to Chinese name + icon URL."""
    if not rank_tier:
        return "未校准", None
    try:
        tier = int(rank_tier)
    except ValueError:
        return "未知", None
    medals = {1: "先锋", 2: "卫士", 3: "中军", 4: "统帅", 5: "传奇", 6: "万古流芳", 7: "超凡入圣", 8: "冠绝一世"}
    medal_num = tier // 10
    medal = medals.get(medal_num, "未知")
    stars = tier % 10
    rank_icon = f"https://www.opendota.com/assets/images/dota2/rank_icons/rank_icon_{medal_num}.png" if medal_num else None
    name = f"{medal} {stars}" if stars else medal
    return name, rank_icon


def get_rank_name_simple(rank_tier):
    """Convert rank tier number to Chinese name."""
    if rank_tier is None:
        return "未校准"
    return RANK_TIERS.get(rank_tier, f"未知 ({rank_tier})")


# ── Core algorithms ──

def calculate_impact_score(match):
    """Calculate impact score for a match (0-100)."""
    try:
        kills = float(match.get("adv_kills") or match.get("kills", 0))
        assists = float(match.get("adv_assists") or match.get("assists", 0))
        deaths = float(match.get("adv_deaths") or match.get("deaths", 0))
        hero_damage = float(match.get("adv_hero_damage") or match.get("hero_damage", 0))
        tower_damage = float(match.get("adv_tower_damage") or match.get("tower_damage", 0))

        base_score = (kills * 1.0 + assists * 0.7 + (hero_damage / 1000) * 0.5 + (tower_damage / 1000) * 1.0) / (deaths + 1)
        normalized_score = min(base_score * 5, 75)

        if match.get("win") == "Win":
            normalized_score *= 1.2

        benchmark_avg = (
            float(match.get("benchmark_gpm_pct", 0)) +
            float(match.get("benchmark_xpm_pct", 0)) +
            float(match.get("benchmark_damage_pct", 0))
        ) / 3
        if benchmark_avg > 75:
            normalized_score *= 1.1

        return min(int(normalized_score), 100)
    except (ValueError, ZeroDivisionError):
        return 0


def get_match_badges(match, impact_score=0):
    """Determine badges for a match."""
    badges = []
    try:
        if impact_score > 80:
            badges.append({"icon": "🔥", "text": "High Impact", "class": "badge-high-impact"})

        hero_damage = float(match.get("adv_hero_damage") or match.get("hero_damage", 0))
        if match.get("win") == "Win" and hero_damage > 20000:
            badges.append({"icon": "⭐", "text": "Carry", "class": "badge-carry"})

        kills = float(match.get("adv_kills") or match.get("kills", 0))
        assists = float(match.get("adv_assists") or match.get("assists", 0))
        deaths = float(match.get("adv_deaths") or match.get("deaths", 0))
        if assists > 15 and deaths < 5 and assists > kills:
            badges.append({"icon": "🛡️", "text": "Support", "class": "badge-support"})
    except (ValueError, TypeError):
        pass
    return badges


def calc_rolling_winrate(matches, window=10):
    """Calculate rolling win rate over a sliding window."""
    chronological = list(reversed(matches[:100]))
    if len(chronological) < window:
        return []
    results = []
    for i in range(window, len(chronological) + 1):
        chunk = chronological[i - window:i]
        wins = sum(1 for m in chunk if m.get("win") == "Win")
        results.append({"index": i, "winrate": round(wins / window * 100, 1)})
    return results


def calc_time_analysis(matches):
    """Analyze win rates by time of day and day of week (UTC+8)."""
    slot_keys = ["凌晨 (0-6)", "上午 (6-12)", "下午 (12-18)", "晚上 (18-24)"]
    time_slots = {k: {"wins": 0, "games": 0} for k in slot_keys}
    day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekdays = {d: {"wins": 0, "games": 0} for d in day_names}

    for m in matches:
        ts = m.get("timestamp")
        if not ts:
            continue
        try:
            if isinstance(ts, str):
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            elif isinstance(ts, (int, float)):
                dt = datetime.utcfromtimestamp(ts)
            else:
                continue
            dt_cn = dt + timedelta(hours=8)
            hour = dt_cn.hour
            if hour < 6:
                slot = slot_keys[0]
            elif hour < 12:
                slot = slot_keys[1]
            elif hour < 18:
                slot = slot_keys[2]
            else:
                slot = slot_keys[3]
            time_slots[slot]["games"] += 1
            if m.get("win") == "Win":
                time_slots[slot]["wins"] += 1
            day_name = day_names[dt_cn.weekday()]
            weekdays[day_name]["games"] += 1
            if m.get("win") == "Win":
                weekdays[day_name]["wins"] += 1
        except (ValueError, TypeError, OSError):
            continue

    time_result = [{"label": k, "games": v["games"], "wins": v["wins"], "winrate": round(v["wins"] / v["games"] * 100, 1) if v["games"] else 0} for k, v in time_slots.items()]
    weekday_result = [{"label": d, "games": weekdays[d]["games"], "wins": weekdays[d]["wins"], "winrate": round(weekdays[d]["wins"] / weekdays[d]["games"] * 100, 1) if weekdays[d]["games"] else 0} for d in day_names]
    return time_result, weekday_result


def calc_recent_trend(matches):
    """Compare last 7 days vs previous 7 days stats."""
    now = datetime.utcnow() + timedelta(hours=8)
    seven_days_ago = now - timedelta(days=7)
    fourteen_days_ago = now - timedelta(days=14)
    recent, previous = [], []

    for m in matches:
        ts = m.get("timestamp")
        if not ts:
            continue
        try:
            if isinstance(ts, str):
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00")) + timedelta(hours=8)
            elif isinstance(ts, (int, float)):
                dt = datetime.utcfromtimestamp(ts) + timedelta(hours=8)
            else:
                continue
            if dt >= seven_days_ago:
                recent.append(m)
            elif dt >= fourteen_days_ago:
                previous.append(m)
        except (ValueError, TypeError, OSError):
            continue

    def calc_stats(game_list):
        if not game_list:
            return {"winrate": 0, "avg_kda": 0, "avg_impact": 0, "games": 0}
        wins = sum(1 for m in game_list if m.get("win") == "Win")
        total_kda = 0
        total_impact = 0
        for m in game_list:
            k = float(m.get("adv_kills") or m.get("kills", 0))
            d = float(m.get("adv_deaths") or m.get("deaths", 0))
            a = float(m.get("adv_assists") or m.get("assists", 0))
            total_kda += (k + a) / max(d, 1)
            total_impact += calculate_impact_score(m)
        n = len(game_list)
        return {"winrate": round(wins / n * 100, 1), "avg_kda": round(total_kda / n, 2), "avg_impact": round(total_impact / n, 1), "games": n}

    rs, ps = calc_stats(recent), calc_stats(previous)
    return {
        "recent": rs, "previous": ps,
        "winrate_diff": round(rs["winrate"] - ps["winrate"], 1),
        "kda_diff": round(rs["avg_kda"] - ps["avg_kda"], 2),
        "impact_diff": round(rs["avg_impact"] - ps["avg_impact"], 1),
    }


def calc_streak(matches):
    """Calculate current win/loss streak."""
    if not matches:
        return 0, ""
    streak_type = matches[0].get("win")
    count = 1
    for m in matches[1:]:
        if m.get("win") == streak_type:
            count += 1
        else:
            break
    return count, "连胜" if streak_type == "Win" else "连败"


def calc_role_performance(matches):
    """Calculate per-role performance stats."""
    role_stats = {}
    for m in matches:
        lr = m.get("role", 0) or m.get("lane_role", 0)
        if lr not in ROLE_NAMES:
            continue
        if lr not in role_stats:
            role_stats[lr] = {"games": 0, "wins": 0, "kills": 0, "deaths": 0, "assists": 0, "impact_total": 0}
        rs = role_stats[lr]
        rs["games"] += 1
        if m.get("win") == "Win":
            rs["wins"] += 1
        rs["kills"] += int(m.get("adv_kills") or m.get("kills", 0))
        rs["deaths"] += int(m.get("adv_deaths") or m.get("deaths", 0))
        rs["assists"] += int(m.get("adv_assists") or m.get("assists", 0))
        rs["impact_total"] += calculate_impact_score(m)

    result = []
    for lr in sorted(role_stats.keys()):
        rs = role_stats[lr]
        g = rs["games"]
        result.append({
            "role": ROLE_NAMES[lr], "lane_role": lr, "games": g,
            "wins": rs["wins"], "losses": g - rs["wins"],
            "win_rate": round(rs["wins"] / g * 100, 1) if g else 0,
            "avg_kills": round(rs["kills"] / g, 1) if g else 0,
            "avg_deaths": round(rs["deaths"] / g, 1) if g else 0,
            "avg_assists": round(rs["assists"] / g, 1) if g else 0,
            "avg_impact": round(rs["impact_total"] / g, 1) if g else 0,
        })
    return result


def enrich_match(m):
    """Add computed fields to a match dict."""
    m["item_icons"] = [get_item_icon_url(m.get(f"item_{i}", 0)) for i in range(6)]
    m["item_neutral_icon"] = get_item_icon_url(m.get("item_neutral", 0))
    m["impact_score"] = calculate_impact_score(m)
    m["badges"] = get_match_badges(m, m["impact_score"])
    effective_role = m.get("role", 0) or m.get("lane_role", 0)
    m["effective_role"] = effective_role
    m["role_name"] = ROLE_SHORT.get(effective_role, "-")
    return m
