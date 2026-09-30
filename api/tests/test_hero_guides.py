"""Candidate equipment must come from actual, same-patch inventory evidence."""

import unittest
from unittest.mock import patch
from fastapi import HTTPException

from routers.hero_guides import _abilities, _catalog, _description, _verified_rank, aggregate_builds, hero_builds, hero_mechanics


CATALOG = _catalog({
    "blink": {"id": 1, "cost": 2250, "dname": "Blink Dagger", "created": False},
    "overwhelming_blink": {"id": 600, "cost": 6800, "dname": "Overwhelming Blink", "created": True},
    "blade_mail": {"id": 127, "cost": 2300, "dname": "Blade Mail", "created": True},
    "black_king_bar": {"id": 116, "cost": 4050, "dname": "Black King Bar", "created": True},
    "boots": {"id": 29, "cost": 500},
    "ultimate_orb": {"id": 24, "cost": 2800, "created": False},
    "neutral": {"id": 900, "cost": 0},
})


def match(match_id=1, patch_id=42, time=100, items=None):
    inventory = items or [1, 127, 116, 29, 0, 0]
    player = {"hero_id": 2, "player_slot": 0, "item_neutral": 900,
              **{f"item_{index}": value for index, value in enumerate(inventory)},
              "purchase_log": [{"key": "blink", "time": time}], "name": "Example"}
    return {"match_id": match_id, "start_time": 10000 + match_id, "duration": 3000, "patch": patch_id,
            "radiant_win": True, "players": [player]}


def profile(account_id, rank=80, leaderboard=100):
    return {"profile": {"account_id": account_id, "personaname": f"Player {account_id}"},
            "rank_tier": rank, "leaderboard_rank": leaderboard, "computed_mmr": 99999}


class HeroGuideTests(unittest.TestCase):
    def test_patch_isolation_does_not_blend_old_builds(self):
        result = aggregate_builds(2, [match(1, 41), match(2), match(3), match(4)], CATALOG)
        self.assertEqual(result["sample"], 3)
        self.assertEqual(result["patch_id"], 42)
        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual(result["candidates"][0]["example_matches"], ["4", "3", "2"])

    def test_inventory_is_six_slots_and_neutral_is_not_a_candidate(self):
        matches = [match(index) for index in range(1, 4)]
        for detail in matches:
            detail["players"][0]["backpack_0"] = 127
        result = aggregate_builds(2, matches, CATALOG)
        self.assertEqual(len(result["matches"][0]["items"]), 6)
        self.assertEqual(result["matches"][0]["neutral"]["item_id"], 900)
        self.assertEqual(result["candidates"][0]["matches"], 3)
        self.assertEqual(result["candidates"][0]["pick_rate"], 100)
        self.assertNotIn(900, [item["item_id"] for item in result["candidates"]])

    def test_duplicate_slots_and_upgraded_blink_count_once(self):
        matches = [match(index, items=[600, 1, 127, 127, 0, 0]) for index in range(1, 4)]
        result = aggregate_builds(2, matches, CATALOG)
        self.assertEqual([item["matches"] for item in result["candidates"]], [3, 3])
        self.assertEqual(result["candidates"][0]["slug"], "blink")

    def test_missing_equipment_is_not_an_empty_inventory(self):
        detail = match()
        del detail["players"][0]["item_5"]
        self.assertEqual(aggregate_builds(2, [detail], CATALOG)["sample"], 0)
        self.assertEqual(aggregate_builds(2, [match()], CATALOG)["candidates"], [])

    def test_purchase_time_needs_three_observed_logs(self):
        matches = [match(1, time=600), match(2, time=1200), match(3, time=1800)]
        result = aggregate_builds(2, matches, CATALOG)
        blink = result["candidates"][0]
        self.assertEqual(blink["purchase_minute"], 20)
        self.assertEqual(blink["timing_sample"], 3)
        del matches[0]["players"][0]["purchase_log"]
        self.assertIsNone(aggregate_builds(2, matches, CATALOG)["candidates"][0]["purchase_minute"])

    def test_upgraded_blink_time_does_not_become_basic_blink_time(self):
        matches = [match(index, items=[600, 127, 0, 0, 0, 0]) for index in range(1, 4)]
        for detail in matches:
            detail["players"][0]["purchase_log"] = [{"key": "overwhelming_blink", "time": 1800}]
        candidate = aggregate_builds(2, matches, CATALOG)["candidates"][0]
        self.assertIsNone(candidate["purchase_minute"])
        self.assertEqual(candidate["timing_sample"], 0)

    def test_unknown_result_does_not_become_a_loss(self):
        matches = [match(index) for index in range(1, 4)]
        for detail in matches:
            detail["radiant_win"] = None
        result = aggregate_builds(2, matches, CATALOG)
        self.assertIsNone(result["matches"][0]["win"])
        self.assertIsNone(result["candidates"][0]["win_rate"])

    def test_missing_team_slot_is_not_assumed_dire(self):
        detail = match()
        del detail["players"][0]["player_slot"]
        self.assertIsNone(aggregate_builds(2, [detail], CATALOG)["matches"][0]["win"])

    def test_repeated_match_cannot_inflate_sample(self):
        detail = match()
        result = aggregate_builds(2, [detail, detail, detail], CATALOG)
        self.assertEqual(result["sample"], 1)
        self.assertEqual(result["candidates"], [])

    def test_unknown_patch_is_not_blended_with_known_patch(self):
        detail = match(4)
        del detail["patch"]
        result = aggregate_builds(2, [match(1), match(2), match(3), detail], CATALOG)
        self.assertIsNone(result["patch_id"])
        self.assertEqual(result["sample"], 1)

    def test_missing_neutral_remains_unknown(self):
        detail = match()
        del detail["players"][0]["item_neutral"]
        self.assertIsNone(aggregate_builds(2, [detail], CATALOG)["matches"][0]["neutral"]["item_id"])

    def test_valve_description_resolves_numbers_and_escapes_markup(self):
        ability = {"special_values": [{"name": "range", "values_float": [100, 200], "values_scepter": [500]}]}
        self.assertEqual(_description("<b>范围</b> %range%", ability), "范围 100/200")
        self.assertEqual(_description("范围 %range%", ability, "scepter"), "范围 500")
        self.assertEqual(_description("概率 20%%", ability), "概率 20%")

    def test_new_hero_source_failure_is_not_reported_as_nonexistent(self):
        with patch("routers.hero_guides._valve", return_value=({}, None, True)):
            with self.assertRaises(HTTPException) as raised:
                hero_mechanics(146)
        self.assertEqual(raised.exception.status_code, 503)

    def test_rank_evidence_requires_identity_immortal_and_a_real_leaderboard_place(self):
        self.assertTrue(_verified_rank(profile(1), 1))
        for record in [profile(2), profile(1, 75), profile(1, None), profile(1, "80"),
                       profile(1, leaderboard=None), profile(1, leaderboard=0), profile(1, leaderboard=True)]:
            with self.subTest(record=record):
                self.assertFalse(_verified_rank(record, 1))

    def test_ordinary_players_and_nonranked_details_cannot_enter_high_rank_inventory(self):
        details, ranks = [], {}
        for index in range(1, 6):
            detail = match(index)
            detail.update(lobby_type=7, game_mode=22)
            detail["players"][0]["account_id"] = index
            ranks[index] = profile(index, rank=75 if index == 1 else 80)
            details.append(detail)
        details[-1]["lobby_type"] = 1
        result = aggregate_builds(2, details, CATALOG, ranks, now=20000)
        self.assertEqual(result["sample"], 3)
        self.assertEqual([row["account_id"] for row in result["matches"]], [4, 3, 2])
        self.assertTrue(all(row["rank_tier"] == 80 for row in result["matches"]))
        self.assertNotIn("computed_mmr", result["matches"][0])

    def test_build_endpoint_rechecks_ranked_hero_time_and_account_instead_of_trusting_query_filters(self):
        now = 2_000_000
        recent = [{"match_id": index, "account_id": index, "start_time": now - index, "leagueid": 100} for index in range(1, 11)]

        def get(path, params=None, **kwargs):
            if path == "/heroes/2/matches":
                return recent, None
            if path == "/rankings":
                return {"rankings": []}, None
            if path == "/constants/items":
                return {item["slug"]: item for item in CATALOG.values()}, None
            if path == "/constants/patch":
                return [{"id": 42, "name": "test"}], None
            if path.startswith("/players/"):
                account_id = int(path.split("/")[2])
                if not path.endswith("/matches"):
                    return profile(account_id), None
                row = {"match_id": account_id, "hero_id": 2, "lobby_type": 7, "game_mode": 22,
                       "start_time": now - account_id, "duration": 3000}
                invalid = [{**row, "match_id": 20, "start_time": now + 10},
                           {**row, "match_id": 21, "start_time": now - 15 * 86400},
                           {**row, "match_id": 22, "lobby_type": 1},
                           {**row, "match_id": 23, "hero_id": 7},
                           {**row, "match_id": 24, "game_mode": 23}]
                return [row, row, *invalid], None
            detail = match(int(path.split("/")[-1]))
            detail["start_time"] = now - detail["match_id"]
            detail.update(lobby_type=7, game_mode=22)
            detail["players"][0]["account_id"] = detail["match_id"]
            return detail, "显示的是缓存数据" if detail["match_id"] == 1 else None

        with patch("routers.hero_guides._cache", {}), patch("routers.hero_guides.time.time", return_value=now), patch("routers.hero_guides._cached_get", side_effect=get) as request:
            result = hero_builds(2)
        self.assertEqual(result["sample"], 8)
        self.assertEqual(result["source"]["attempted"], 8)
        self.assertEqual(result["source"]["status"], "partial")
        self.assertEqual(result["source"]["scope"], "ranked_immortal_players")
        self.assertEqual(result["source"]["players_verified"], 8)
        self.assertEqual(len(result["source"]["players"]), 8)
        self.assertEqual(result["matches"][0]["match_type"], "天梯排位")
        paths = {call.args[0] for call in request.call_args_list}
        self.assertNotIn("/matches/20", paths)
        self.assertNotIn("/matches/21", paths)
        self.assertNotIn("/matches/22", paths)
        self.assertNotIn("/matches/23", paths)
        self.assertNotIn("/matches/24", paths)
        self.assertNotIn("/matches/9", paths)
        for call in request.call_args_list:
            if call.args[0].startswith("/players/") and call.args[0].endswith("/matches"):
                self.assertEqual(call.args[1], {"hero_id": 2, "lobby_type": 7, "date": 14, "limit": 4})

    def test_stale_or_missing_rank_cannot_be_promoted_by_league_appearance(self):
        now = 2_000_000

        def get(path, params=None, **kwargs):
            if path == "/heroes/2/matches":
                return [{"match_id": account, "account_id": account, "start_time": now - account, "leagueid": 100}
                        for account in [1, 2, 3]], None
            if path.startswith("/players/"):
                account = int(path.split("/")[-1])
                return profile(account, rank=75 if account == 1 else None if account == 2 else 80), "缓存数据" if account == 3 else None
            return {}, None

        with patch("routers.hero_guides._cache", {}) as cache, patch("routers.hero_guides.time.time", return_value=now), patch("routers.hero_guides._cached_get", side_effect=get) as request:
            result = hero_builds(2)
            calls = request.call_count
            self.assertEqual(hero_builds(2), result)
            self.assertEqual(request.call_count, calls)
            self.assertEqual(cache["ranked_builds:2"]["ttl"], 60)
        self.assertEqual(result["sample"], 0)
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["source"]["players_verified"], 0)
        self.assertEqual(result["source"]["status"], "unavailable")
        self.assertFalse(any(call.args[0].endswith("/matches") and call.args[0].startswith("/players/") for call in request.call_args_list))

    def test_match_detail_identity_mismatch_cannot_supply_equipment(self):
        now = 2_000_000

        def get(path, params=None, **kwargs):
            if path == "/rankings":
                return {"rankings": [{"account_id": 1}]}, None
            if path == "/players/1":
                return profile(1), None
            if path == "/players/1/matches":
                return [{"match_id": 1, "hero_id": 2, "lobby_type": 7, "game_mode": 22, "start_time": now - 1, "duration": 3000}], None
            if path == "/matches/1":
                detail = match()
                detail.update(start_time=now - 1, lobby_type=7, game_mode=22)
                detail["players"][0]["account_id"] = 99
                return detail, None
            return {}, None

        with patch("routers.hero_guides._cache", {}), patch("routers.hero_guides.time.time", return_value=now), patch("routers.hero_guides._cached_get", side_effect=get):
            result = hero_builds(2)
        self.assertEqual(result["sample"], 0)
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["source"]["players"], [])
        self.assertEqual(result["source"]["status"], "insufficient")

    def test_build_endpoint_unavailable_source_does_not_fabricate_candidates(self):
        with patch("routers.hero_guides._cache", {}), patch("routers.hero_guides._cached_get", return_value=(None, "请求超时")):
            result = hero_builds(2)
        self.assertEqual(result["sample"], 0)
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["source"]["status"], "unavailable")

    def test_combo_is_withheld_when_current_skills_change(self):
        hero = {"id": 7, "name": "npc_dota_hero_earthshaker", "name_loc": "撼地者", "abilities": []}
        with patch("routers.hero_guides._valve", return_value=({"heroes": [hero]}, 100, False)):
            self.assertIsNone(hero_mechanics(7)["practice"])
        self.assertEqual(_abilities({"abilities": [{"name": "test", "name_loc": "测试", "behavior": "2"}]})[0]["kind"], "被动")


if __name__ == "__main__":
    unittest.main()
