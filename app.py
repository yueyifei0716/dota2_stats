"""
Dota 2 Stats Web Dashboard - 中文版
Flask web application to view your Dota 2 statistics.
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for
import subprocess
import sys
import requests
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import notion_db as nc
import notion_cache as cache
from fetch_dota_stats import fetch_player_rankings

app = Flask(__name__)

# Rank tier names (first digit = medal, second digit = stars)
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

# Rank tier English names for medal images
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


def get_rank_name_simple(rank_tier):
    """Convert rank tier number to Chinese name (simple version)."""
    if rank_tier is None:
        return "未校准"
    return RANK_TIERS.get(rank_tier, f"未知 ({rank_tier})")


def read_matches():
    """Read matches from Notion (cached)."""
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
    """Read profile from Notion (cached)."""
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
    """Read hero stats from Notion (cached)."""
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
    """Read MMR history from Notion (cached)."""
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


# Item ID to name mapping for icons (from OpenDota API)
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
    # Neutral items
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
    # Neutral token enhancements
    1584: "enhancement_alert", 1585: "enhancement_brawny", 1586: "enhancement_tough",
    1587: "enhancement_feverish", 1588: "enhancement_fleetfooted", 1589: "enhancement_crude",
    1590: "enhancement_boundless", 1591: "enhancement_wise", 1592: "enhancement_timeless",
    1593: "enhancement_greedy", 1594: "enhancement_vampiric", 1595: "enhancement_keen_eyed",
    1596: "enhancement_evolved", 1597: "enhancement_titanic",
    # More neutrals
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
    2192: "martyrs_plate", 2193: "gossamer_cape"
}


def get_item_icon_url(item_id):
    """Get item icon URL from item ID."""
    if not item_id or item_id == 0 or item_id == "0":
        return ""
    try:
        item_id = int(item_id)
    except ValueError:
        return ""
    item_name = ITEM_NAMES.get(item_id, "")
    if item_name:
        return f"https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/items/{item_name}.png"
    return ""


def get_rank_name(rank_tier):
    """Convert rank tier to Chinese name."""
    if not rank_tier:
        return "未校准", None
    try:
        tier = int(rank_tier)
    except ValueError:
        return "未知", None

    medals = {
        1: "先锋", 2: "卫士", 3: "中军", 4: "统帅",
        5: "传奇", 6: "万古流芳", 7: "超凡入圣", 8: "冠绝一世"
    }
    medal_icons = {
        1: "herald", 2: "guardian", 3: "crusader", 4: "archon",
        5: "legend", 6: "ancient", 7: "divine", 8: "immortal"
    }
    medal_num = tier // 10
    medal = medals.get(medal_num, "未知")
    stars = tier % 10
    icon_name = medal_icons.get(medal_num, "")
    rank_icon = f"https://www.opendota.com/assets/images/dota2/rank_icons/rank_icon_{medal_num}.png" if icon_name else None
    name = f"{medal} {stars}" if stars else medal
    return name, rank_icon


def calculate_impact_score(match):
    """Calculate impact score for a match (0-100)."""
    try:
        # Use advanced data fields (adv_*) if available, fall back to base fields
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


@app.route("/")
def index():
    profile = read_profile()
    matches = read_matches()
    hero_stats = read_hero_stats()
    mmr_history = read_mmr_history()

    # Get hero filter from query param
    hero_filter = request.args.get("hero", "")
    role_filter = request.args.get("role", "")

    # Get unique heroes for filter dropdown
    all_heroes = sorted(set((m.get("hero_cn", ""), m.get("hero_icon", "")) for m in matches), key=lambda x: x[0])

    # Filter matches by hero and/or role if specified
    filtered_matches = matches
    if hero_filter:
        filtered_matches = [m for m in filtered_matches if m.get("hero_cn") == hero_filter]
    if role_filter:
        try:
            role_filter_int = int(role_filter)
            filtered_matches = [m for m in filtered_matches if (m.get("role") or m.get("lane_role", 0)) == role_filter_int]
        except ValueError:
            pass

    # Short role names for match table display
    role_short_names = {1: "Pos 1", 2: "Pos 2", 3: "Pos 3", 4: "Pos 4", 5: "Pos 5"}

    # Add computed fields (items, impact scores, badges) to matches
    for m in filtered_matches:
        # Build item icons from consolidated match data
        m["item_icons"] = [
            get_item_icon_url(m.get("item_0", 0)),
            get_item_icon_url(m.get("item_1", 0)),
            get_item_icon_url(m.get("item_2", 0)),
            get_item_icon_url(m.get("item_3", 0)),
            get_item_icon_url(m.get("item_4", 0)),
            get_item_icon_url(m.get("item_5", 0)),
        ]
        m["item_neutral_icon"] = get_item_icon_url(m.get("item_neutral", 0))

        # Impact score and badges (advanced fields already on match)
        m["impact_score"] = calculate_impact_score(m)
        m["badges"] = get_match_badges(m, m["impact_score"])

        # Role name for display (prefer GPM-based role, fall back to lane_role)
        effective_role = m.get("role", 0) or m.get("lane_role", 0)
        m["effective_role"] = effective_role
        m["role_name"] = role_short_names.get(effective_role, "-")

    # Calculate recent stats (last 20 games)
    recent = matches[:20]
    recent_wins = sum(1 for m in recent if m.get("win") == "Win")
    recent_losses = len(recent) - recent_wins

    # Calculate filtered stats
    filtered_wins = sum(1 for m in filtered_matches if m.get("win") == "Win")
    filtered_losses = len(filtered_matches) - filtered_wins

    # Calculate streaks
    current_streak = 0
    streak_type = None
    for m in matches:
        if streak_type is None:
            streak_type = m.get("win")
            current_streak = 1
        elif m.get("win") == streak_type:
            current_streak += 1
        else:
            break

    # Hero frequency in recent games
    hero_freq = defaultdict(lambda: {"count": 0, "icon": "", "name": ""})
    for m in recent:
        hero_cn = m.get("hero_cn", "未知")
        hero_freq[hero_cn]["count"] += 1
        hero_freq[hero_cn]["icon"] = m.get("hero_icon", "")
        hero_freq[hero_cn]["name"] = hero_cn
    most_played_recent = sorted(hero_freq.values(), key=lambda x: -x["count"])[:5]

    # Sort hero stats by games
    hero_stats_sorted = sorted(hero_stats, key=lambda x: -int(x.get("games", 0)))[:15]

    # Best and worst heroes (min 10 games)
    qualified_heroes = [h for h in hero_stats if int(h.get("games", 0)) >= 10]
    best_heroes = sorted(qualified_heroes, key=lambda x: -float(x.get("win_rate", 0)))[:5]
    worst_heroes = sorted(qualified_heroes, key=lambda x: float(x.get("win_rate", 0)))[:5]

    # Prepare MMR history for chart
    mmr_dates = [h.get("date", "")[:10] for h in mmr_history]
    mmr_values = [int(h.get("mmr", 0)) for h in mmr_history]

    # Fetch rank history from OpenDota
    ratings = fetch_player_ratings()
    rank_history_dates = []
    rank_history_values = []
    rank_history_labels = []
    for r in ratings:
        date_str = r.get("time", "")[:10]
        tier = r.get("rank_tier", 0)
        rank_history_dates.append(date_str)
        rank_history_values.append(tier)
        rank_history_labels.append(get_rank_name_simple(tier))

    # Fetch hero rankings from OpenDota
    rankings = fetch_player_rankings()
    # Build hero_id to name mapping from hero_stats
    hero_id_to_name = {}
    hero_id_to_icon = {}
    for h in hero_stats:
        hid = h.get("hero_id")
        if hid:
            hero_id_to_name[int(hid)] = h.get("hero_cn", "未知")
            hero_id_to_icon[int(hid)] = h.get("hero_icon", "")

    # Process rankings - top 10 heroes by percentile
    top_rankings = []
    for r in rankings[:10]:
        hero_id = r.get("hero_id")
        percent = r.get("percent_rank", 0) * 100  # Convert to percentage
        top_rankings.append({
            "hero_id": hero_id,
            "hero_cn": hero_id_to_name.get(hero_id, f"英雄 {hero_id}"),
            "hero_icon": hero_id_to_icon.get(hero_id, ""),
            "percent_rank": percent,
            "top_percent": 100 - percent,  # Top X%
        })

    # Role performance stats (GPM-based role 1-5, fallback to lane_role)
    role_names = {1: "优势路 (Pos 1)", 2: "中路 (Pos 2)", 3: "劣势路 (Pos 3)", 4: "辅助 (Pos 4)", 5: "纯辅助 (Pos 5)"}
    role_stats = {}
    for m in matches:
        lr = m.get("role", 0) or m.get("lane_role", 0)
        if lr not in role_names:
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

    role_performance = []
    for lr in sorted(role_stats.keys()):
        rs = role_stats[lr]
        g = rs["games"]
        role_performance.append({
            "role": role_names[lr],
            "lane_role": lr,
            "games": g,
            "wins": rs["wins"],
            "losses": g - rs["wins"],
            "win_rate": round(rs["wins"] / g * 100, 1) if g else 0,
            "avg_kills": round(rs["kills"] / g, 1) if g else 0,
            "avg_deaths": round(rs["deaths"] / g, 1) if g else 0,
            "avg_assists": round(rs["assists"] / g, 1) if g else 0,
            "avg_impact": round(rs["impact_total"] / g, 1) if g else 0,
        })

    rank_name, rank_icon = get_rank_name(profile.get("rank_tier"))

    return render_template("index.html",
        profile=profile,
        rank_name=rank_name,
        rank_icon=rank_icon,
        matches=filtered_matches[:100],
        all_heroes=all_heroes,
        hero_filter=hero_filter,
        role_filter=role_filter,
        filtered_wins=filtered_wins,
        filtered_losses=filtered_losses,
        recent_wins=recent_wins,
        recent_losses=recent_losses,
        current_streak=current_streak,
        streak_type="连胜" if streak_type == "Win" else "连败",
        most_played_recent=most_played_recent,
        hero_stats=hero_stats_sorted,
        best_heroes=best_heroes,
        worst_heroes=worst_heroes,
        mmr_history=mmr_history,
        mmr_dates=mmr_dates,
        mmr_values=mmr_values,
        rank_history_dates=rank_history_dates,
        rank_history_values=rank_history_values,
        rank_history_labels=rank_history_labels,
        role_performance=role_performance
    )


@app.route("/update_mmr", methods=["POST"])
def update_mmr():
    """Update MMR via web form."""
    mmr = request.form.get("mmr")
    result = request.form.get("result", "")
    if mmr:
        try:
            mmr_int = int(mmr)
            nc.append_mmr_history(mmr_int, result)
            cache.invalidate("mmr_history")
        except ValueError:
            pass
    return redirect(url_for("index"))


@app.route("/calibrate_mmr", methods=["POST"])
def calibrate_mmr():
    """Calibrate MMR to actual value via web form."""
    mmr = request.form.get("mmr")
    if mmr:
        try:
            mmr_int = int(mmr)
            # Update profile with calibrated MMR
            nc.update_profile({"current_mmr": mmr_int, "estimated_mmr": mmr_int})
            # Add calibration record to history
            nc.append_mmr_history(mmr_int, "Calibrate")
            # Invalidate cache
            cache.invalidate("profile")
            cache.invalidate("mmr_history")
            print(f"MMR calibrated to {mmr_int} via web")
        except ValueError:
            pass
    return redirect(url_for("index"))


@app.route("/api/matches")
def api_matches():
    return jsonify(read_matches())


@app.route("/api/heroes")
def api_heroes():
    return jsonify(read_hero_stats())


@app.route("/api/mmr_history")
def api_mmr_history():
    return jsonify(read_mmr_history())


@app.route("/api/match_notes", methods=["GET", "POST"])
def api_match_notes():
    """Get or save match notes."""
    if request.method == "POST":
        data = request.get_json()
        if data and "match_id" in data:
            match_id = str(data["match_id"])
            note = data.get("note", "")
            nc.update_match_note(match_id, note)
            cache.invalidate("matches")
            return jsonify({"success": True, "message": "笔记已保存"})
        return jsonify({"success": False, "message": "缺少match_id"})
    else:
        match_id = request.args.get("match_id")
        if match_id:
            matches = read_matches()
            for m in matches:
                if m.get("match_id") == match_id:
                    return jsonify({"note": m.get("note", "")})
            return jsonify({"note": ""})
        # Return all notes as dict
        matches = read_matches()
        return jsonify({m["match_id"]: m.get("note", "") for m in matches})


@app.route("/update_data", methods=["POST"])
def update_data():
    """Run fetch script to update match data."""
    try:
        fetch_items = request.form.get("fetch_items") == "1"
        script_path = Path(__file__).parent / "fetch_dota_stats.py"

        args = [sys.executable, str(script_path)]
        if fetch_items:
            args.append("--items")
        else:
            args.append("200")  # Default limit

        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        # Invalidate cache after update
        cache.invalidate()

        if result.returncode == 0:
            return jsonify({"success": True, "message": "数据更新成功!"})
        else:
            return jsonify({"success": False, "message": f"更新失败: {result.stderr}"})
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "message": "更新超时，请稍后重试"})
    except Exception as e:
        return jsonify({"success": False, "message": f"错误: {str(e)}"})


if __name__ == "__main__":
    app.run(debug=True, port=5001)
